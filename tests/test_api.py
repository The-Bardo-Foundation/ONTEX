import pytest

from app.db.models import ClinicalTrial, TrialStatus


@pytest.mark.asyncio
async def test_get_trials_returns_list(test_client):
    r = await test_client.get("/api/v1/trials")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_trail_returns_404_for_missing(test_client):
    r = await test_client.get("/api/v1/trail?trail_id=NCT_MISSING")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_trail_returns_404_for_non_approved(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000001",
                brief_title="Pending Trial",
                status=TrialStatus.PENDING_REVIEW,
            )
        )

    r = await test_client.get("/api/v1/trail?trail_id=NCT00000001")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_trail_returns_approved_trial(test_client, db_engine):
    async with db_engine.begin() as conn:
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

    r = await test_client.get("/api/v1/trail?trail_id=NCT00000002")
    assert r.status_code == 200
    body = r.json()
    assert "result" in body
    trial = body["result"][0]
    assert trial["NCTId"] == "NCT00000002"
    assert trial["BriefTitle"] == "Approved Osteosarcoma Trial"
    assert trial["CustomBriefSummary"] == "Patient-friendly summary."
    assert trial["key_information"] == "Key facts here."
    assert trial["CentralContactEMail"] == "contact@example.com"


@pytest.mark.asyncio
async def test_debug_ingestion_endpoint(test_client, monkeypatch):
    called = {"called": False}

    async def fake_run():
        called["called"] = True

    import app.services.ingestion as ingestion

    monkeypatch.setattr(ingestion, "run_daily_ingestion", fake_run)

    r = await test_client.post("/api/v1/debug/run-ingestion")
    assert r.status_code == 200
    assert r.json().get("status") == "started"
    assert called["called"]
