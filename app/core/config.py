import os
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
    OPENAI_API_KEY: str = "Not Set"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password"
    ENVIRONMENT: str = "local"  # local, staging, production

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_ignore_empty=True,
        extra="ignore"
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

