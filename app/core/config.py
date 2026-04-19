import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """Determine which .env file to load based on environment"""
    env = os.getenv("ENVIRONMENT", "local")

    if env == "railway" or env == "production":
        return ".env.railway"
    return ".env.local"


class Settings(BaseSettings):
    # Use a local async sqlite DB for local development by default.
    DATABASE_URL: str = "sqlite+aiosqlite:///./ontex.db"
    OPENROUTER_API_KEY: str = "Not Set"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: Optional[str] = None  # Must be set via environment variable in production
    ENVIRONMENT: str = "local"  # local, staging, production

    # CORS: comma-separated list of allowed origins for the API.
    # Override via ALLOWED_ORIGINS env var in production.
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Ingestion pipeline settings
    # SEARCH_TERMS can be overridden via env var as JSON: SEARCH_TERMS='["osteosarcoma","bone sarcoma"]'
    SEARCH_TERMS: list[str] = ["osteosarcoma"]
    INGESTION_SCHEDULE_HOURS: int = 24
    AI_MODEL: str = "openai/gpt-4o-mini"
    CONFIDENCE_THRESHOLD: float = 0.7
    PAGE_SIZE: int = 100

    model_config = SettingsConfigDict(
        env_file=get_env_file(), env_ignore_empty=True, extra="ignore"
    )


settings = Settings()

# Basic sanity check to help developers catch mistaken env values (e.g. using an
# HTTP URL instead of a SQLAlchemy DB URL). If a clearly invalid scheme is
# detected, print a helpful error to stderr so it's obvious during startup.
if settings.DATABASE_URL.startswith("http"):
    import sys

    print(
        "ERROR: DATABASE_URL appears to be an HTTP URL."
        " Set DATABASE_URL to a valid SQLAlchemy URL like",
        "'postgresql+asyncpg://user:pass@host/db' or",
        "'sqlite+aiosqlite:///./ontex.db'",
        file=sys.stderr,
    )
