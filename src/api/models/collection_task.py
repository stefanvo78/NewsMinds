"""
CollectionTask model - tracks background article collection jobs.

Each row represents one collection run (either collect-all or single-source).
Status is shared across gunicorn workers and Azure replicas via the database.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.api.models.source import Source


class CollectionTask(Base, TimestampMixin):
    """
    A background collection task.

    - source_id IS NULL  → collect-all task
    - source_id IS NOT NULL → single-source task
    """

    __tablename__ = "collection_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # NULL = collect-all; set = single-source collection
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sources.id"),
        nullable=True,
        index=True,
    )

    running: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Result payload (JSON) — shape varies by task type
    result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationship to Source (optional, for single-source tasks)
    source: Mapped[Optional["Source"]] = relationship(
        "Source",
        lazy="selectin",
    )
