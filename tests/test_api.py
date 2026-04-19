import json
from unittest.mock import AsyncMock

import pytest

from app.db.models import ClinicalTrial, IngestionEvent, TrialStatus


# ──────────────────────────────────────────────────────────
# GET /trail (WordPress PHP endpoint)
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# GET /trials (paginated list)
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_trials_returns_paginated_response(test_client):
    r = await test_client.get("/api/v1/trials")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 0
    assert body["items"] == []


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
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT00000010"
    assert body["items"][0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_get_trials_unauthenticated_forces_approved_status(test_client, db_engine):
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
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT00000020"
    assert body["items"][0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_get_trials_filters_by_status_pending_review_for_admin(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000022", brief_title="Approved Trial", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT00000023", brief_title="Pending Trial", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.get(
        "/api/v1/trials?status=PENDING_REVIEW",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT00000023"
    assert body["items"][0]["status"] == "PENDING_REVIEW"


# ──────────────────────────────────────────────────────────
# PATCH /trials/{nct_id} (backwards-compat endpoint)
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# GET /trials/review-queue
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_review_queue_returns_pending_only(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000001", brief_title="Pending Trial", status=TrialStatus.PENDING_REVIEW
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000002", brief_title="Approved Trial", status=TrialStatus.APPROVED
            )
        )

    r = await test_client.get("/api/v1/trials/review-queue")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["nct_id"] == "NCT10000001"
    assert body[0]["status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_get_review_queue_includes_ingestion_event(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000003",
                brief_title="Updated Trial",
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=IngestionEvent.UPDATED,
            )
        )

    r = await test_client.get("/api/v1/trials/review-queue")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["ingestion_event"] == "UPDATED"


# ──────────────────────────────────────────────────────────
# GET /trials/{nct_id}
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_trial_detail_full_fields(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000010",
                brief_title="Full Detail Trial",
                brief_summary="Official summary.",
                custom_brief_summary="Custom summary.",
                phase="Phase 2",
                ai_relevance_label="confident",
                ai_relevance_reason="Matches criteria.",
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=IngestionEvent.NEW,
            )
        )

    r = await test_client.get("/api/v1/trials/NCT10000010")
    assert r.status_code == 200
    body = r.json()
    assert body["nct_id"] == "NCT10000010"
    assert body["brief_title"] == "Full Detail Trial"
    assert body["brief_summary"] == "Official summary."
    assert body["custom_brief_summary"] == "Custom summary."
    assert body["phase"] == "Phase 2"
    assert body["ai_relevance_label"] == "confident"
    assert body["ai_relevance_reason"] == "Matches criteria."
    assert body["ingestion_event"] == "NEW"


@pytest.mark.asyncio
async def test_get_trial_detail_not_found(test_client):
    r = await test_client.get("/api/v1/trials/NCT_FAKE_999")
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────
# PATCH /trials/{nct_id}/approve
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_sets_approved_at_and_by(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000020", brief_title="Trial A", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch(
        "/api/v1/trials/NCT10000020/approve",
        json={"username": "dr_smith", "reviewer_notes": "Looks good."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "APPROVED"
    assert body["approved_by"] == "admin@local"
    assert body["approved_at"] is not None
    assert body["reviewer_notes"] == "Looks good."


@pytest.mark.asyncio
async def test_approve_saves_custom_fields(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000021", brief_title="Trial B", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch(
        "/api/v1/trials/NCT10000021/approve",
        json={"username": "admin", "custom_brief_summary": "Edited by reviewer."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["custom_brief_summary"] == "Edited by reviewer."
    assert body["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_approve_not_found(test_client):
    r = await test_client.patch(
        "/api/v1/trials/NCT_MISSING/approve", json={"username": "admin"}
    )
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────
# PATCH /trials/{nct_id}/reject
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_sets_rejected_at_and_by(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT10000030", brief_title="Trial C", status=TrialStatus.PENDING_REVIEW
            )
        )

    r = await test_client.patch(
        "/api/v1/trials/NCT10000030/reject",
        json={"username": "dr_jones", "reviewer_notes": "Not relevant."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "REJECTED"
    assert body["rejected_by"] == "admin@local"
    assert body["rejected_at"] is not None
    assert body["reviewer_notes"] == "Not relevant."


@pytest.mark.asyncio
async def test_reject_not_found(test_client):
    r = await test_client.patch(
        "/api/v1/trials/NCT_MISSING/reject", json={"username": "admin"}
    )
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────
# GET /trials — search, filter, sort, pagination
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_trials_pagination(test_client, db_engine):
    async with db_engine.begin() as conn:
        for i in range(25):
            await conn.execute(
                ClinicalTrial.__table__.insert().values(
                    nct_id=f"NCT2000{i:04d}",
                    brief_title=f"Trial {i}",
                    status=TrialStatus.APPROVED,
                )
            )

    r1 = await test_client.get("/api/v1/trials?page=1&page_size=10")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["total"] == 25
    assert len(body1["items"]) == 10
    assert body1["page"] == 1

    r3 = await test_client.get("/api/v1/trials?page=3&page_size=10")
    assert r3.status_code == 200
    body3 = r3.json()
    assert len(body3["items"]) == 5


@pytest.mark.asyncio
async def test_get_trials_rejects_invalid_page(test_client):
    r = await test_client.get("/api/v1/trials?page=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_trials_rejects_invalid_page_size(test_client):
    r = await test_client.get("/api/v1/trials?page_size=101")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_trials_search_q(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000001",
                brief_title="Osteosarcoma Phase II Study",
                status=TrialStatus.APPROVED,
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000002",
                brief_title="Unrelated Diabetes Trial",
                status=TrialStatus.APPROVED,
            )
        )

    r = await test_client.get("/api/v1/trials?q=osteosarcoma")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT30000001"


@pytest.mark.asyncio
async def test_get_trials_unauthenticated_ignores_ingestion_event_filter(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000008",
                brief_title="Pending New Trial",
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=IngestionEvent.NEW,
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000009",
                brief_title="Approved Trial",
                status=TrialStatus.APPROVED,
            )
        )

    r = await test_client.get("/api/v1/trials?ingestion_event=NEW")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT30000009"
    assert body["items"][0]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_get_trials_filter_ingestion_event(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000010",
                brief_title="New Trial",
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=IngestionEvent.NEW,
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000011",
                brief_title="Updated Trial",
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=IngestionEvent.UPDATED,
            )
        )

    r = await test_client.get(
        "/api/v1/trials?ingestion_event=NEW",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["nct_id"] == "NCT30000010"

    r_updated = await test_client.get(
        "/api/v1/trials?ingestion_event=UPDATED",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r_updated.status_code == 200
    updated_body = r_updated.json()
    assert updated_body["total"] == 1
    assert updated_body["items"][0]["nct_id"] == "NCT30000011"


@pytest.mark.asyncio
async def test_get_trials_sort_brief_title(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000020", brief_title="Zebra Trial", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT30000021", brief_title="Alpha Trial", status=TrialStatus.APPROVED
            )
        )

    r = await test_client.get("/api/v1/trials?sort_by=brief_title")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["brief_title"] == "Alpha Trial"
    assert items[1]["brief_title"] == "Zebra Trial"


def _parse_sse_events(raw_text: str) -> list[dict]:
    events = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.mark.asyncio
async def test_ingestion_run_stream_rejects_unauthenticated_when_auth_enabled(test_client, monkeypatch):
    monkeypatch.delenv("SKIP_AUTH_FOR_TESTS", raising=False)
    r = await test_client.get("/api/v1/ingestion/run-stream")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingestion_run_stream_returns_error_event_when_already_running(test_client, monkeypatch):
    import app.api.endpoints as endpoints

    release_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(endpoints, "_try_acquire_ingestion_lock", AsyncMock(return_value=False))
    monkeypatch.setattr(endpoints, "_release_ingestion_lock", release_mock)

    r = await test_client.get(
        "/api/v1/ingestion/run-stream",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    events = _parse_sse_events(r.text)
    assert len(events) == 1
    assert events[0]["step"] == "error"
    assert "already running" in events[0]["message"].lower()
    release_mock.assert_not_called()


@pytest.mark.asyncio
async def test_ingestion_run_stream_emits_progress_and_complete_events(test_client, monkeypatch):
    import app.api.endpoints as endpoints
    import app.services.ingestion as ingestion

    async def fake_run_daily_ingestion(progress_callback=None):
        if progress_callback:
            await progress_callback({"step": "progress", "message": "started"})

    monkeypatch.setattr(endpoints, "_try_acquire_ingestion_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(endpoints, "_release_ingestion_lock", AsyncMock(return_value=None))
    monkeypatch.setattr(ingestion, "run_daily_ingestion", fake_run_daily_ingestion)

    r = await test_client.get(
        "/api/v1/ingestion/run-stream",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    events = _parse_sse_events(r.text)
    steps = [event["step"] for event in events]
    assert "progress" in steps
    assert "complete" in steps


@pytest.mark.asyncio
async def test_ingestion_run_stream_emits_error_without_complete_on_failure(test_client, monkeypatch):
    import app.api.endpoints as endpoints
    import app.services.ingestion as ingestion

    async def failing_run_daily_ingestion(progress_callback=None):
        raise RuntimeError("ingestion failed")

    monkeypatch.setattr(endpoints, "_try_acquire_ingestion_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(endpoints, "_release_ingestion_lock", AsyncMock(return_value=None))
    monkeypatch.setattr(ingestion, "run_daily_ingestion", failing_run_daily_ingestion)

    r = await test_client.get(
        "/api/v1/ingestion/run-stream",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    events = _parse_sse_events(r.text)
    steps = [event["step"] for event in events]
    assert "error" in steps
    assert "complete" not in steps
