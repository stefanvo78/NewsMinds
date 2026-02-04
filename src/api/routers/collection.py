"""
Collection endpoints - trigger news article collection.

Collection runs in a **thread pool** so it doesn't block the async event-loop
(the collection pipeline contains synchronous CPU-bound work: feedparser,
sentence-transformer embeddings, synchronous Qdrant client calls).

Status is stored in the database (collection_tasks table) so it's shared
across gunicorn worker processes and Azure Container App replicas.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from src.api.core.database import AsyncSessionLocal
from src.api.core.deps import CurrentUser, DbSession
from src.api.models import CollectionTask, Source
from src.collection.service import collect_all, collect_from_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["Collection"])


# ---------------------------------------------------------------------------
# Status serialization
# ---------------------------------------------------------------------------

def _task_to_status(task: CollectionTask | None) -> dict:
    """
    Convert a CollectionTask ORM object to the API status response dict.

    Returns a consistent shape regardless of whether a task exists,
    so the frontend always gets the same fields.
    """
    if task is None:
        return {
            "running": False,
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
    return {
        "running": task.running,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "result": task.result,
        "error": task.error,
    }


# ---------------------------------------------------------------------------
# Background helpers — run blocking collection in a thread
# ---------------------------------------------------------------------------

async def _finish_task(task_id: str, result: dict | None, error: str | None) -> None:
    """Update a CollectionTask row as finished (success or failure)."""
    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                select(CollectionTask).where(
                    CollectionTask.id == uuid.UUID(task_id)
                )
            )
        ).scalar_one()
        row.running = False
        row.finished_at = datetime.now(UTC)
        row.result = result
        row.error = error
        await db.commit()


async def _run_collect_all_in_thread(task_id: str) -> None:
    """Spawn blocking collection work in a thread so the event-loop stays free."""
    try:
        result = await asyncio.to_thread(_collect_all_sync)
        await _finish_task(task_id, result=result, error=None)
        logger.info("Background collection completed successfully")
    except Exception as e:
        logger.error(f"Background collection failed: {e}")
        await _finish_task(task_id, result=None, error=str(e))


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


async def _run_collect_source_in_thread(
    task_id: str, source_id: str, source_name: str
) -> None:
    """Spawn single-source collection in a thread."""
    try:
        stats = await asyncio.to_thread(_collect_source_sync, source_id)
        await _finish_task(
            task_id, result={"source": source_name, **stats}, error=None
        )
        logger.info(f"Background collection for source '{source_name}' completed")
    except Exception as e:
        logger.error(f"Background collection for source '{source_name}' failed: {e}")
        await _finish_task(task_id, result=None, error=str(e))


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
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Kick off article collection from all active sources.

    Runs in a background thread so the response is immediate.
    Poll GET /collection/status to track progress.
    """
    # Check if a collect-all task is already running
    existing = (
        await db.execute(
            select(CollectionTask).where(
                CollectionTask.source_id.is_(None),
                CollectionTask.running.is_(True),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return {
            "message": "Collection already in progress",
            "status": "running",
            "started_at": existing.started_at.isoformat()
            if existing.started_at
            else None,
        }

    # Create a new task record
    task = CollectionTask(
        source_id=None,
        running=True,
        started_at=datetime.now(UTC),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Fire-and-forget in a background thread
    asyncio.create_task(_run_collect_all_in_thread(str(task.id)))
    return {"message": "Collection started", "status": "running"}


@router.get("/status")
async def get_collection_status(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Return the current collection status (most recent collect-all task)."""
    task = (
        await db.execute(
            select(CollectionTask)
            .where(CollectionTask.source_id.is_(None))
            .order_by(CollectionTask.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _task_to_status(task)


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
    # Verify source exists and is collectible
    source = (
        await db.execute(select(Source).where(Source.id == source_id))
    ).scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.source_type == "static":
        raise HTTPException(
            status_code=400,
            detail="Cannot collect from a static source. Update source_type first.",
        )

    # Check if already running for this source
    existing = (
        await db.execute(
            select(CollectionTask).where(
                CollectionTask.source_id == source_id,
                CollectionTask.running.is_(True),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return {
            "message": f"Collection already in progress for '{source.name}'",
            "status": "running",
            "started_at": existing.started_at.isoformat()
            if existing.started_at
            else None,
        }

    # Create a new task record
    task = CollectionTask(
        source_id=source_id,
        running=True,
        started_at=datetime.now(UTC),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Fire-and-forget in a background thread
    asyncio.create_task(
        _run_collect_source_in_thread(str(task.id), str(source_id), source.name)
    )
    return {"message": f"Collection started for '{source.name}'", "status": "running"}


@router.get("/status/{source_id}")
async def get_source_collection_status(
    source_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Return the collection status for a specific source (most recent task)."""
    task = (
        await db.execute(
            select(CollectionTask)
            .where(CollectionTask.source_id == source_id)
            .order_by(CollectionTask.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _task_to_status(task)
