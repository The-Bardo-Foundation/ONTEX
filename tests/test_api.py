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
async def test_get_trials_returns_empty_list_when_no_trials(test_client):
    r = await test_client.get("/api/v1/trials")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_trials_filters_by_status_approved(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000010", brief_title="Approved Trial", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000011", brief_title="Pending Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.get("/api/v1/trials?status=APPROVED")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["nct_id"] == "NCT00000010"
    assert body[0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_get_trials_filters_by_status_pending_review(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000020", brief_title="Approved Trial", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000021", brief_title="Pending Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.get("/api/v1/trials?status=PENDING_REVIEW")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["nct_id"] == "NCT00000021"
    assert body[0]["status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_patch_trial_approve_transition(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000030", brief_title="A Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch("/api/v1/trials/NCT00000030", json={"status": "APPROVED"})
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_patch_trial_reject_transition(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000040", brief_title="A Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch("/api/v1/trials/NCT00000040", json={"status": "REJECTED"})
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_patch_trial_not_found_returns_404(test_client):
    r = await test_client.patch(
        "/api/v1/trials/NCT_DOES_NOT_EXIST", json={"status": "APPROVED"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_trial_updates_custom_brief_summary(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000050", brief_title="A Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch(
        "/api/v1/trials/NCT00000050",
        json={"status": "APPROVED", "custom_brief_summary": "Admin note."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "APPROVED"
    assert body["custom_brief_summary"] == "Admin note."


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
