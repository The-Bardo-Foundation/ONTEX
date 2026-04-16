"""
Pytest configuration and fixtures for test suite.
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

def pytest_configure(config):
    """Set environment variables before any app module is imported.

    database.py creates engine = create_async_engine(settings.DATABASE_URL)
    at module level. This hook fires before collection imports test modules,
    ensuring the singleton engine points to in-memory SQLite, not a real DB.
    OPENAI_API_KEY must be a non-sentinel value so AIClient.__init__ doesn't raise.
    """
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["OPENAI_API_KEY"] = "sk-test-not-real"
    os.environ["SKIP_MIGRATIONS"] = "1"

# Ensure repository root is on sys.path so `import app` works in CI
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    """A fresh SQLite engine with all tables created, scoped to one test."""
    from app.db.database import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_client(db_engine, monkeypatch):
    """
    AsyncClient wired to a fresh per-test SQLite DB via get_db dependency override.

    Ingestion is patched to a no-op so tests don't hit the external API.
    Individual tests may re-patch run_daily_ingestion after receiving this fixture
    if they need to inspect calls (monkeypatch.setattr overwrites the noop).
    """
    import app.services.ingestion as ingestion

    monkeypatch.setattr(ingestion, "run_daily_ingestion", AsyncMock(return_value=None))
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    from app.db.database import get_db
    from app.main import app

    async def override_get_db():
        async with AsyncSession(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
