import pytest

from app.db.models import (
    ClinicalTrial,
    IngestionEvent,
    IrrelevantTrial,
    SearchKeyword,
    TrialKeywordMatch,
    TrialStatus,
)


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


# ── POST /ingestion/start + GET /ingestion/status ─────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_start_rejects_unauthenticated(test_client, monkeypatch):
    monkeypatch.delenv("SKIP_AUTH_FOR_TESTS", raising=False)
    r = await test_client.post("/api/v1/ingestion/start")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingestion_start_returns_started_true(test_client):
    r = await test_client.post(
        "/api/v1/ingestion/start",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    assert r.json() == {"started": True}


@pytest.mark.asyncio
async def test_ingestion_start_returns_409_when_already_running(test_client):
    import app.api.endpoints as endpoints
    await endpoints._ingestion_lock.acquire()
    try:
        r = await test_client.post(
            "/api/v1/ingestion/start",
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 409
    finally:
        endpoints._ingestion_lock.release()


@pytest.mark.asyncio
async def test_ingestion_status_returns_state(test_client):
    import app.api.endpoints as endpoints
    import copy
    endpoints._ingestion_status.update({
        "running": False,
        "paused": False,
        "stop_requested": False,
        "steps": copy.deepcopy(endpoints._STEP_TEMPLATE),
        "error": None,
        "summary": None,
    })
    r = await test_client.get(
        "/api/v1/ingestion/status",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is False
    assert body["paused"] is False
    assert body["stop_requested"] is False
    assert body["error"] is None
    assert body["summary"] is None
    assert len(body["steps"]) == 4
    assert all(s["state"] == "waiting" for s in body["steps"])


@pytest.mark.asyncio
async def test_ingestion_status_rejects_unauthenticated(test_client, monkeypatch):
    monkeypatch.delenv("SKIP_AUTH_FOR_TESTS", raising=False)
    r = await test_client.get("/api/v1/ingestion/status")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingestion_pause_resume_stop_require_running(test_client):
    pause = await test_client.post(
        "/api/v1/ingestion/pause",
        headers={"Authorization": "Bearer test-token"},
    )
    assert pause.status_code == 409

    resume = await test_client.post(
        "/api/v1/ingestion/resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resume.status_code == 409

    stop = await test_client.post(
        "/api/v1/ingestion/stop",
        headers={"Authorization": "Bearer test-token"},
    )
    assert stop.status_code == 409


@pytest.mark.asyncio
async def test_ingestion_pause_resume_stop_when_running(test_client):
    import app.api.endpoints as endpoints

    endpoints._ingestion_status["running"] = True
    endpoints._ingestion_status["paused"] = False
    endpoints._ingestion_status["stop_requested"] = False
    endpoints._ingestion_pause_event.set()
    endpoints._ingestion_stop_requested = False

    pause = await test_client.post(
        "/api/v1/ingestion/pause",
        headers={"Authorization": "Bearer test-token"},
    )
    assert pause.status_code == 200
    assert pause.json() == {"paused": True}
    assert endpoints._ingestion_status["paused"] is True
    assert not endpoints._ingestion_pause_event.is_set()

    resume = await test_client.post(
        "/api/v1/ingestion/resume",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resume.status_code == 200
    assert resume.json() == {"paused": False}
    assert endpoints._ingestion_status["paused"] is False
    assert endpoints._ingestion_pause_event.is_set()

    stop = await test_client.post(
        "/api/v1/ingestion/stop",
        headers={"Authorization": "Bearer test-token"},
    )
    assert stop.status_code == 200
    assert stop.json() == {"stop_requested": True}
    assert endpoints._ingestion_status["stop_requested"] is True
    assert endpoints._ingestion_stop_requested is True


# ── GET /ingestion/history ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_history_rejects_unauthenticated(test_client, monkeypatch):
    monkeypatch.delenv("SKIP_AUTH_FOR_TESTS", raising=False)
    r = await test_client.get("/api/v1/ingestion/history")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingestion_history_returns_empty_when_no_runs(test_client):
    r = await test_client.get(
        "/api/v1/ingestion/history",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["recent_runs"] == []
    assert body["next_run"] is None  # no scheduler in test env


# ── Keyword management ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_keyword_crud_flow(test_client):
    create = await test_client.post("/api/v1/keywords", json={"term": " Osteosarcoma "})
    assert create.status_code == 200
    created = create.json()
    assert created["term"] == "osteosarcoma"
    assert created["is_active"] is True

    dup = await test_client.post("/api/v1/keywords", json={"term": "osteosarcoma"})
    assert dup.status_code == 409

    kw_id = created["id"]
    toggle = await test_client.patch(f"/api/v1/keywords/{kw_id}", json={"is_active": False})
    assert toggle.status_code == 200
    assert toggle.json()["is_active"] is False

    listing = await test_client.get("/api/v1/keywords")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["term"] == "osteosarcoma"

    deleted = await test_client.delete(f"/api/v1/keywords/{kw_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


@pytest.mark.asyncio
async def test_keywords_list_seeds_default_when_empty(test_client):
    listing = await test_client.get("/api/v1/keywords")
    assert listing.status_code == 200
    body = listing.json()
    assert len(body) >= 1
    assert any(item["term"] == "osteosarcoma" for item in body)


@pytest.mark.asyncio
async def test_delete_keyword_prunes_non_approved_but_keeps_approved(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            SearchKeyword.__table__.insert().values(id=1, term="osteosarcoma", is_active=True)
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT_KEEP_APPROVED", brief_title="Keep", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT_DROP_PENDING", brief_title="Drop", status=TrialStatus.PENDING_REVIEW
            )
        )
        await conn.execute(
            IrrelevantTrial.__table__.insert().values(
                nct_id="NCT_DROP_IRRELEVANT", brief_title="Drop irrelevant"
            )
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(
                nct_id="NCT_KEEP_APPROVED", keyword_id=1
            )
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(
                nct_id="NCT_DROP_PENDING", keyword_id=1
            )
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(
                nct_id="NCT_DROP_IRRELEVANT", keyword_id=1
            )
        )

    deleted = await test_client.delete("/api/v1/keywords/1")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert deleted.json()["pruned_trials"] == 2

    approved_check = await test_client.get("/api/v1/trials?status=APPROVED")
    assert approved_check.status_code == 200
    approved_ids = {item["nct_id"] for item in approved_check.json()["items"]}
    assert "NCT_KEEP_APPROVED" in approved_ids

    pending_admin = await test_client.get(
        "/api/v1/trials?status=PENDING_REVIEW",
        headers={"Authorization": "Bearer test-token"},
    )
    assert pending_admin.status_code == 200
    assert pending_admin.json()["total"] == 0

    irrelevant_admin = await test_client.get("/api/v1/irrelevant-trials")
    assert irrelevant_admin.status_code == 200
    assert irrelevant_admin.json()["total"] == 0


@pytest.mark.asyncio
async def test_admin_visibility_hides_trials_only_on_inactive_keywords(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            SearchKeyword.__table__.insert().values(id=10, term="active-term", is_active=True)
        )
        await conn.execute(
            SearchKeyword.__table__.insert().values(id=11, term="inactive-term", is_active=False)
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT_PENDING_ACTIVE", brief_title="Pending active", status=TrialStatus.PENDING_REVIEW
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT_PENDING_INACTIVE", brief_title="Pending inactive", status=TrialStatus.PENDING_REVIEW
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT_APPROVED_INACTIVE", brief_title="Approved inactive", status=TrialStatus.APPROVED
            )
        )
        await conn.execute(
            IrrelevantTrial.__table__.insert().values(
                nct_id="NCT_IRRELEVANT_ACTIVE", brief_title="Irrelevant active"
            )
        )
        await conn.execute(
            IrrelevantTrial.__table__.insert().values(
                nct_id="NCT_IRRELEVANT_INACTIVE", brief_title="Irrelevant inactive"
            )
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(nct_id="NCT_PENDING_ACTIVE", keyword_id=10)
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(nct_id="NCT_PENDING_INACTIVE", keyword_id=11)
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(nct_id="NCT_APPROVED_INACTIVE", keyword_id=11)
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(nct_id="NCT_IRRELEVANT_ACTIVE", keyword_id=10)
        )
        await conn.execute(
            TrialKeywordMatch.__table__.insert().values(nct_id="NCT_IRRELEVANT_INACTIVE", keyword_id=11)
        )

    review_queue = await test_client.get("/api/v1/trials/review-queue")
    assert review_queue.status_code == 200
    assert [item["nct_id"] for item in review_queue.json()] == ["NCT_PENDING_ACTIVE"]

    pending_admin = await test_client.get(
        "/api/v1/trials?status=PENDING_REVIEW",
        headers={"Authorization": "Bearer test-token"},
    )
    pending_ids = {item["nct_id"] for item in pending_admin.json()["items"]}
    assert pending_ids == {"NCT_PENDING_ACTIVE"}

    approved_admin = await test_client.get(
        "/api/v1/trials?status=APPROVED",
        headers={"Authorization": "Bearer test-token"},
    )
    approved_ids = {item["nct_id"] for item in approved_admin.json()["items"]}
    assert "NCT_APPROVED_INACTIVE" in approved_ids

    irrelevant_admin = await test_client.get("/api/v1/irrelevant-trials")
    assert irrelevant_admin.status_code == 200
    irrelevant_ids = {item["nct_id"] for item in irrelevant_admin.json()["items"]}
    assert irrelevant_ids == {"NCT_IRRELEVANT_ACTIVE"}
