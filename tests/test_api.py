import pathlib
import sys

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
    from app.db.database import Base, engine
    from app.main import app, scheduler

    # Ensure tables exist for the sqlite test DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/trials")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    # Shutdown scheduler if it's running
    if scheduler.running:
        scheduler.shutdown()


@pytest.mark.asyncio
async def test_get_trail_returns_404_for_missing(tmp_path, monkeypatch):
    db_file = tmp_path / "test3.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    import app.services.ingestion as ingestion

    async def noop():
        return None

    monkeypatch.setattr(ingestion, "run_daily_ingestion", noop)

    from app.db.database import Base, engine
    from app.main import app, scheduler

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/trail?trail_id=NCT_MISSING")
        assert r.status_code == 404

    if scheduler.running:
        scheduler.shutdown()


@pytest.mark.asyncio
async def test_get_trail_returns_404_for_non_approved(tmp_path, monkeypatch):
    db_file = tmp_path / "test4.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    import app.services.ingestion as ingestion

    async def noop():
        return None

    monkeypatch.setattr(ingestion, "run_daily_ingestion", noop)

    from app.db.database import Base, engine
    from app.db.models import ClinicalTrial, TrialStatus
    from app.main import app, scheduler

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000001",
                brief_title="Pending Trial",
                status=TrialStatus.PENDING_REVIEW,
            )
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/trail?trail_id=NCT00000001")
        assert r.status_code == 404

    if scheduler.running:
        scheduler.shutdown()


@pytest.mark.asyncio
async def test_get_trail_returns_approved_trial(tmp_path, monkeypatch):
    db_file = tmp_path / "test5.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SKIP_MIGRATIONS", "1")

    import app.services.ingestion as ingestion

    async def noop():
        return None

    monkeypatch.setattr(ingestion, "run_daily_ingestion", noop)

    from app.db.database import Base, engine
    from app.db.models import ClinicalTrial, TrialStatus
    from app.main import app, scheduler

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000002",
                brief_title="Approved Osteosarcoma Trial",
                brief_summary="A phase II trial.",
                custom_brief_summary="Patient-friendly summary.",
                key_information="Key facts here.",
                central_contact_email="contact@example.com",
                status=TrialStatus.APPROVED,
            )
        )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/trail?trail_id=NCT00000002")
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        trial = body["result"][0]
        assert trial["NCTId"] == "NCT00000002"
        assert trial["BriefTitle"] == "Approved Osteosarcoma Trial"
        assert trial["CustomBriefSummary"] == "Patient-friendly summary."
        assert trial["key_information"] == "Key facts here."
        assert trial["CentralContactEMail"] == "contact@example.com"

    if scheduler.running:
        scheduler.shutdown()


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

    from app.db.database import Base, engine
    from app.main import app, scheduler

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/api/v1/debug/run-ingestion")
        assert r.status_code == 200
        assert r.json().get("status") == "started"

    assert called["called"]

    # Shutdown scheduler if it's running
    if scheduler.running:
        scheduler.shutdown()
