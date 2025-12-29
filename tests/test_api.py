import os
import sys
import pathlib
import pytest

# Ensure repository root is on sys.path so `import app` works in CI
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_trials_returns_list(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    # Patch ingestion function to a no-op before importing the app
    import app.services.ingestion as ingestion

    async def noop():
        return None

    monkeypatch.setattr(ingestion, "run_daily_ingestion", noop)

    # Import app after env is configured
    from app.main import app
    from app.db.database import engine, Base

    # Ensure tables exist for the sqlite test DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/trials")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_debug_ingestion_endpoint(monkeypatch, tmp_path):
    db_file = tmp_path / "test2.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    import app.services.ingestion as ingestion
    called = {"called": False}

    async def fake_run():
        called["called"] = True

    monkeypatch.setattr(ingestion, "run_daily_ingestion", fake_run)

    from app.main import app
    from app.db.database import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/api/v1/debug/run-ingestion")
        assert r.status_code == 200
        assert r.json().get("status") == "started"

    assert called["called"]
