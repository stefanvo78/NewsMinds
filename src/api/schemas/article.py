"""
Pydantic schemas for Article API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ArticleCreate(BaseModel):
    """Schema for creating a new article."""

    source_id: uuid.UUID
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=1, max_length=1024)
    content: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = Field(default=None, max_length=255)
    published_at: Optional[datetime] = None
    fetched_at: datetime


class ArticleUpdate(BaseModel):
    """Schema for updating an article (all fields optional)."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    content: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = Field(default=None, max_length=255)
    published_at: Optional[datetime] = None


class ArticleResponse(BaseModel):
    """Schema for returning article data."""

    id: uuid.UUID
    source_id: uuid.UUID
    title: str
    url: str
    content: Optional[str]
    summary: Optional[str]
    author: Optional[str]
    published_at: Optional[datetime]
    fetched_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleListResponse(BaseModel):
    """Schema for paginated article list."""

    items: list[ArticleResponse]
    total: int
    page: int
    per_page: int
