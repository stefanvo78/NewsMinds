"""
Base model class for all SQLAlchemy models.

This provides:
- Common columns (id, created_at, updated_at)
- Consistent naming conventions
- A declarative base for model inheritance
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    SQLAlchemy 2.0 uses DeclarativeBase instead of declarative_base().
    All models inherit from this class to get:
    - Automatic table name generation
    - Common columns
    - Type hints support with Mapped[]
    """
    
    # Automatically generate table names from class names
    # UserSession -> user_session
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name (CamelCase -> snake_case)."""
        name = cls.__name__
        # Insert underscore before uppercase letters and lowercase everything
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns.
    
    Usage:
        class User(Base, TimestampMixin):
            ...
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
