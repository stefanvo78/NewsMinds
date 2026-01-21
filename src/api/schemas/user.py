"""
Pydantic schemas for User API endpoints.

Schemas define the shape of data for:
- Request validation (what clients send)
- Response serialization (what we return)
- OpenAPI documentation (auto-generated)
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# --- Request Schemas ---

class UserCreate(BaseModel):
    """Schema for creating a new user (registration)."""
    
    email: EmailStr  # Pydantic validates email format automatically
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    """Schema for updating user profile (all fields optional)."""
    
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=255)


# --- Response Schemas ---

class UserResponse(BaseModel):
    """Schema for returning user data (excludes password)."""
    
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Allow creating from SQLAlchemy model instances
    model_config = ConfigDict(from_attributes=True)


# --- Auth Schemas ---

class Token(BaseModel):
    """JWT token response."""
    
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload (decoded content)."""
    
    sub: uuid.UUID  # Subject (user ID)
    exp: datetime   # Expiration time
