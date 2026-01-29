"""
Pydantic schemas for Source API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    """Schema for creating a new source."""

    name: str = Field(min_length=1, max_length=255)
    url: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = None
    is_active: bool = True
    source_type: str = Field(default="static", pattern="^(rss|newsapi|static)$")
    source_config: dict = Field(default_factory=dict)

class SourceUpdate(BaseModel):
    """Schema for updating a source (all fields optional)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    url: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    source_type: Optional[str] = Field(default=None, pattern="^(rss|newsapi|static)$")
    source_config: Optional[dict] = None



class SourceResponse(BaseModel):
    """Schema for returning source data."""

    id: uuid.UUID
    name: str
    url: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    source_type: str
    source_config: dict
