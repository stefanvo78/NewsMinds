"""
Collection endpoints - trigger news article collection.

Collection runs in a **thread pool** so it doesn't block the async event-loop
(the collection pipeline contains synchronous CPU-bound work: feedparser,
sentence-transformer embeddings, synchronous Qdrant client calls).

Status is persisted to JSON files in /tmp so it's shared across gunicorn
worker processes.
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from src.api.core.database import AsyncSessionLocal
from src.api.core.deps import CurrentUser, DbSession
from src.api.models import Source
from src.collection.service import collect_all, collect_from_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["Collection"])


# ---------------------------------------------------------------------------
# File-based status store (shared across gunicorn workers)
# ---------------------------------------------------------------------------
_STATUS_DIR = Path("/tmp/newsminds_collection")
_STATUS_DIR.mkdir(parents=True, exist_ok=True)

_GLOBAL_STATUS_FILE = _STATUS_DIR / "global_status.json"


def _default_status() -> dict:
    return {
        "running": False,
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }


def _read_status(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_status()


def _write_status(path: Path, status: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(status))
    tmp.rename(path)


def _source_status_file(source_id: str) -> Path:
    return _STATUS_DIR / f"source_{source_id}.json"


# Per-process asyncio locks (protect the file read-check-write sequence)
_collect_all_lock = asyncio.Lock()
_source_locks: dict[str, asyncio.Lock] = {}


def _get_source_lock(source_id: str) -> asyncio.Lock:
    if source_id not in _source_locks:
        _source_locks[source_id] = asyncio.Lock()
    return _source_locks[source_id]


# ---------------------------------------------------------------------------
# Background helpers — run blocking collection in a thread
# ---------------------------------------------------------------------------

async def _run_collect_all_in_thread() -> None:
    """Spawn blocking collection work in a thread so the event-loop stays free."""
    try:
        result = await asyncio.to_thread(_collect_all_sync)
        status = _read_status(_GLOBAL_STATUS_FILE)
        status["result"] = result
        status["error"] = None
        status["running"] = False
        status["finished_at"] = datetime.now(UTC).isoformat()
        _write_status(_GLOBAL_STATUS_FILE, status)
        logger.info("Background collection completed successfully")
    except Exception as e:
        logger.error(f"Background collection failed: {e}")
        status = _read_status(_GLOBAL_STATUS_FILE)
        status["result"] = None
        status["error"] = str(e)
        status["running"] = False
        status["finished_at"] = datetime.now(UTC).isoformat()
        _write_status(_GLOBAL_STATUS_FILE, status)


def _collect_all_sync() -> dict:
    """Run collect_all inside a new event-loop on the worker thread."""
    import asyncio as _asyncio

    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_collect_all_async())
    finally:
        loop.close()


async def _collect_all_async() -> dict:
    """Async helper that creates its own DB session."""
    async with AsyncSessionLocal() as db:
        return await collect_all(db)


async def _run_collect_source_in_thread(source_id: str, source_name: str) -> None:
    """Spawn single-source collection in a thread."""
    status_file = _source_status_file(source_id)
    try:
        stats = await asyncio.to_thread(_collect_source_sync, source_id)
        status = _read_status(status_file)
        status["result"] = {"source": source_name, **stats}
        status["error"] = None
        status["running"] = False
        status["finished_at"] = datetime.now(UTC).isoformat()
        _write_status(status_file, status)
        logger.info(f"Background collection for source '{source_name}' completed")
    except Exception as e:
        logger.error(f"Background collection for source '{source_name}' failed: {e}")
        status = _read_status(status_file)
        status["result"] = None
        status["error"] = str(e)
        status["running"] = False
        status["finished_at"] = datetime.now(UTC).isoformat()
        _write_status(status_file, status)


def _collect_source_sync(source_id: str) -> dict:
    """Run collect_from_source inside a new event-loop on the worker thread."""
    import asyncio as _asyncio

    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_collect_source_async(source_id))
    finally:
        loop.close()


async def _collect_source_async(source_id: str) -> dict:
    """Async helper that creates its own DB session for single-source."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source).where(Source.id == uuid.UUID(source_id))
        )
        source = result.scalar_one_or_none()
        if not source:
            raise ValueError(f"Source {source_id} not found")
        return await collect_from_source(source, db)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/collect-all")
async def trigger_collect_all(
    current_user: CurrentUser,
) -> dict:
    """
    Kick off article collection from all active sources.

    Runs in a background thread so the response is immediate.
    Poll GET /collection/status to track progress.
    """
    async with _collect_all_lock:
        status = _read_status(_GLOBAL_STATUS_FILE)
        if status["running"]:
            return {
                "message": "Collection already in progress",
                "status": "running",
                "started_at": status["started_at"],
            }

        new_status = {
            "running": True,
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": None,
            "result": None,
            "error": None,
        }
        _write_status(_GLOBAL_STATUS_FILE, new_status)

    # Fire-and-forget: schedule on the event loop but don't await
    asyncio.create_task(_run_collect_all_in_thread())
    return {"message": "Collection started", "status": "running"}


@router.get("/status")
async def get_collection_status(
    current_user: CurrentUser,
) -> dict:
    """Return the current collection status."""
    return _read_status(_GLOBAL_STATUS_FILE)


@router.post("/collect/{source_id}")
async def trigger_collect_source(
    source_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Kick off article collection from a specific source.

    Runs in a background thread so the response is immediate.
    Poll GET /collection/status/{source_id} to track progress.
    """
    sid = str(source_id)

    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.source_type == "static":
        raise HTTPException(
            status_code=400,
            detail="Cannot collect from a static source. Update source_type first.",
        )

    lock = _get_source_lock(sid)
    async with lock:
        status_file = _source_status_file(sid)
        status = _read_status(status_file)
        if status["running"]:
            return {
                "message": f"Collection already in progress for '{source.name}'",
                "status": "running",
                "started_at": status["started_at"],
            }

        new_status = {
            "running": True,
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": None,
            "result": None,
            "error": None,
        }
        _write_status(status_file, new_status)

    # Fire-and-forget: schedule on the event loop but don't await
    asyncio.create_task(_run_collect_source_in_thread(sid, source.name))
    return {"message": f"Collection started for '{source.name}'", "status": "running"}


@router.get("/status/{source_id}")
async def get_source_collection_status(
    source_id: uuid.UUID,
    current_user: CurrentUser,
) -> dict:
    """Return the collection status for a specific source."""
    return _read_status(_source_status_file(str(source_id)))
