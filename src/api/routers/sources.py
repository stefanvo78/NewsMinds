"""
Source management endpoints (CRUD).
"""

import uuid

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select

from src.api.core.deps import DbSession, CurrentUser
from src.api.models import Source
from src.api.schemas import SourceCreate, SourceUpdate, SourceResponse


router = APIRouter(prefix="/sources", tags=["Sources"])


@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    source_data: SourceCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Source:
    """Create a new news source."""
    # Check if source name already exists
    result = await db.execute(select(Source).where(Source.name == source_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this name already exists",
        )

    source = Source(**source_data.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/", response_model=list[SourceResponse])
async def list_sources(
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = Query(False),
) -> list[Source]:
    """List all news sources with pagination."""
    query = select(Source)
    if active_only:
        query = query.where(Source.is_active.is_(True))
    # MSSQL requires ORDER BY when using OFFSET/LIMIT
    query = query.order_by(Source.name).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: uuid.UUID, db: DbSession) -> Source:
    """Get a specific source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: uuid.UUID,
    source_data: SourceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Source:
    """Update a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Update only provided fields
    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    await db.delete(source)
    await db.commit()
