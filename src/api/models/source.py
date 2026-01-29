"""
News Source model for tracking news providers.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.api.models.article import Article


class Source(Base, TimestampMixin):
    """
    News source/provider (e.g., BBC, CNN, Reuters).

    Sources are the origin of articles. Each article belongs to one source.
    """

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Source identification
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # URL of the news source
    url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )

    # Description of the source
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Whether we're actively scraping this source
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationship to articles (one source has many articles)
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="source",
        lazy="selectin",
    )

    # Type of source: "rss", "newsapi", or "static"
    source_type: Mapped[str] = mapped_column(
        String(50),
        default="static",
        nullable=False,
    )

    # Configuration specific to source type (JSON)
    # RSS:     {"feed_url": "https://feeds.bbci.co.uk/news/rss.xml"}
    # NewsAPI: {"query": "artificial intelligence", "language": "en"}
    # Static:  {} (no auto-collection)
    source_config: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
