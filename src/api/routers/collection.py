"""
Collection endpoints - trigger news article collection.
"""

import uuid

from fastapi import APIRouter, HTTPException
from src.api.core.deps import DbSession, CurrentUser
from src.api.models import Source
from src.collection.service import collect_all, collect_from_source
from sqlalchemy import select

router = APIRouter(prefix="/collection", tags=["Collection"])


@router.post("/collect-all")
async def trigger_collect_all(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Collect articles from all active, configured sources.

    This fetches new articles from RSS feeds, NewsAPI, etc.,
    stores them in the database, and ingests them into Qdrant.
    """
    result = await collect_all(db)
    return result


@router.post("/collect/{source_id}")
async def trigger_collect_source(
    source_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Collect articles from a specific source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.source_type == "static":
        raise HTTPException(
            status_code=400,
            detail="Cannot collect from a static source. Update source_type first.",
        )

    stats = await collect_from_source(source, db)
    return {"source": source.name, **stats}
