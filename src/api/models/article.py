"""
Article model for news articles.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.api.models.source import Source


class Article(Base, TimestampMixin):
    """
    News article scraped from a source.

    Articles are the core content of the platform. Each article:
    - Belongs to one Source
    - Has content that can be analyzed by AI agents
    - Tracks when it was published and fetched
    """

    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key to source
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False,
        index=True,
    )

    # Article metadata
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(1024),
        unique=True,  # Prevent duplicate articles
        index=True,
        nullable=False,
    )

    # Article content
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,  # May be null if only metadata is fetched
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,  # AI-generated summary
    )

    # Author info
    author: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # Publication date from the source
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,  # When we scraped it
    )

    # Relationship back to source
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="articles",
    )
