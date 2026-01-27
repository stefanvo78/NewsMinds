"""Add TOTP secret and default admin user

Revision ID: b1234567890a
Revises: a6dfe335ffc8
Create Date: 2026-01-27 10:00:00.000000

"""

import os
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from passlib.context import CryptContext

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1234567890a"
down_revision: str | Sequence[str] | None = "a6dfe335ffc8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Password hashing (same as in security.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    """Add totp_secret column and create default admin user."""
    # Add TOTP secret column for 2FA
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(length=32), nullable=True),
    )

    # Create default admin user
    # Password is read from environment variable or uses a secure default
    admin_email = os.getenv("ADMIN_EMAIL", "admin@newsminds.local")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_password:
        # Generate a random password if not provided
        import secrets
        admin_password = secrets.token_urlsafe(24)
        print(f"\n{'='*60}")
        print("DEFAULT ADMIN USER CREATED")
        print(f"{'='*60}")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print(f"{'='*60}")
        print("IMPORTANT: Save this password! It won't be shown again.")
        print("You should enable 2FA immediately after first login.")
        print(f"{'='*60}\n")

    hashed_password = pwd_context.hash(admin_password)

    # Insert admin user
    # UUID must be stored as 32-char hex string (no hyphens) for SQLite compatibility
    admin_uuid = uuid.uuid4().hex  # hex format without hyphens
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :hashed_password, :full_name, :is_active, :is_superuser, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ).bindparams(
            id=admin_uuid,
            email=admin_email,
            hashed_password=hashed_password,
            full_name="Administrator",
            is_active=True,
            is_superuser=True,
        )
    )


def downgrade() -> None:
    """Remove totp_secret column and admin user."""
    # Remove admin user
    op.execute(
        sa.text("DELETE FROM users WHERE email = 'admin@newsminds.local'")
    )

    # Remove TOTP secret column
    op.drop_column("users", "totp_secret")
