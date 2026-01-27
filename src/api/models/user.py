"""
User model for authentication and profile data.
"""

import uuid
from typing import Optional

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.api.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User account for authentication.

    Table: user (auto-generated from class name)
    """

    __tablename__ = "users"  # Explicit plural table name

    # Primary key using UUID (more secure than sequential integers)
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,  # Index for fast lookups
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # 2FA (TOTP) - stores the secret key for authenticator apps
    totp_secret: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
