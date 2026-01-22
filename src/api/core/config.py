"""
Application configuration using Pydantic Settings.

Pydantic Settings automatically reads from:
1. Environment variables
2. .env file (if python-dotenv is installed)

Usage:
    from src.api.core.config import settings
    print(settings.DATABASE_URL)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "NewsMinds API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-me-in-production"  # For JWT signing
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database (Azure SQL)
    DATABASE_URL: str = ""  # Will be loaded from Key Vault in production

    # Redis
    REDIS_URL: str = ""

    # Azure Key Vault
    KEY_VAULT_URL: str = ""

    # Tell Pydantic to read from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only create one Settings instance,
    which is important because reading env vars is relatively slow.
    """
    return Settings()


# Convenience: import settings directly
settings = get_settings()
