import pytest

from app.db.models import ClinicalTrial, IngestionEvent, IrrelevantTrial, TrialStatus


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
    # Trial is now in irrelevant_trials — no status field on response
    assert "status" not in body
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
    assert body["error"] is None
    assert body["summary"] is None
    assert len(body["steps"]) == 4
    assert all(s["state"] == "waiting" for s in body["steps"])


@pytest.mark.asyncio
async def test_ingestion_status_rejects_unauthenticated(test_client, monkeypatch):
    monkeypatch.delenv("SKIP_AUTH_FOR_TESTS", raising=False)
    r = await test_client.get("/api/v1/ingestion/status")
    assert r.status_code == 401


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


# ── GET /trials/statistics ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_statistics_empty_db_returns_zeros(test_client):
    r = await test_client.get("/api/v1/trials/statistics")
    assert r.status_code == 200
    body = r.json()
    assert body["approved_by_admin"] == 0
    assert body["rejected_by_admin"] == 0
    assert body["pending_review"] == 0
    assert body["ai_auto_rejected"] == 0
    assert body["total"] == 0
    assert body["ai_confident_approval_rate"] is None
    assert body["by_ai_label"] == []


@pytest.mark.asyncio
async def test_statistics_counts_and_ai_correlation(test_client, db_engine):
    async with db_engine.begin() as conn:
        # Human-approved trials (AI deemed relevant)
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT40000001", brief_title="Approved confident A",
                status=TrialStatus.APPROVED, ai_relevance_label="confident",
                approved_by="admin@local",
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT40000002", brief_title="Approved confident B",
                status=TrialStatus.APPROVED, ai_relevance_label="confident",
                approved_by="admin@local",
            )
        )
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT40000003", brief_title="Approved unsure",
                status=TrialStatus.APPROVED, ai_relevance_label="unsure",
                approved_by="admin@local",
            )
        )
        # Pending trial
        await conn.execute(
            ClinicalTrial.__table__.insert().values(
                nct_id="NCT40000004", brief_title="Pending unsure",
                status=TrialStatus.PENDING_REVIEW, ai_relevance_label="unsure",
            )
        )
        # Human-rejected trial (AI said confident, reviewer disagreed)
        await conn.execute(
            IrrelevantTrial.__table__.insert().values(
                nct_id="NCT40000005", brief_title="Human-rejected confident",
                ai_relevance_label="confident", rejected_by="admin@local",
            )
        )
        # AI auto-rejected trial (rejected_by is NULL)
        await conn.execute(
            IrrelevantTrial.__table__.insert().values(
                nct_id="NCT40000006", brief_title="AI-rejected",
                ai_relevance_label="reject", rejected_by=None,
            )
        )

    r = await test_client.get("/api/v1/trials/statistics")
    assert r.status_code == 200
    body = r.json()

    assert body["approved_by_admin"] == 3
    assert body["rejected_by_admin"] == 1
    assert body["pending_review"] == 1
    assert body["ai_auto_rejected"] == 1
    assert body["total"] == 6
    # 2 confident approved, 1 confident human-rejected -> 2/3
    assert body["ai_confident_approval_rate"] == pytest.approx(2 / 3)

    by_label = {row["label"]: row for row in body["by_ai_label"]}
    assert by_label["confident"] == {"label": "confident", "approved": 2, "rejected": 1, "pending": 0}
    assert by_label["unsure"] == {"label": "unsure", "approved": 1, "rejected": 0, "pending": 1}
    # AI auto-rejected trials (rejected_by NULL) are not part of the human matrix
    assert "reject" not in by_label


# ── GET /trials/insights ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insights_empty_db(test_client):
    r = await test_client.get("/api/v1/trials/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["confident_error_rate"] is None
    assert body["unsure_approval_rate"] is None
    assert body["false_negative_count"] == 0
    assert body["confident_false_positives"] == []
    assert body["unsure_resolved"] == []
    assert body["unsure_patterns"] == []


@pytest.mark.asyncio
async def test_insights_rates_and_patterns(test_client, db_engine):
    async with db_engine.begin() as conn:
        # Confident: 2 approved, 1 human-rejected -> error rate 1/3
        await conn.execute(ClinicalTrial.__table__.insert().values(
            nct_id="NCT50000001", brief_title="C approved 1", status=TrialStatus.APPROVED,
            ai_relevance_label="confident", approved_by="admin@local",
        ))
        await conn.execute(ClinicalTrial.__table__.insert().values(
            nct_id="NCT50000002", brief_title="C approved 2", status=TrialStatus.APPROVED,
            ai_relevance_label="confident", approved_by="admin@local",
        ))
        await conn.execute(IrrelevantTrial.__table__.insert().values(
            nct_id="NCT50000003", brief_title="C rejected", ai_relevance_label="confident",
            rejected_by="admin@local", reviewer_notes="Not actually relevant",
        ))
        # Unsure: 1 approved, 1 rejected (both PHASE1) -> approval rate 1/2, pattern bucket
        await conn.execute(ClinicalTrial.__table__.insert().values(
            nct_id="NCT50000004", brief_title="U approved", status=TrialStatus.APPROVED,
            ai_relevance_label="unsure", phase="PHASE1", approved_by="admin@local",
        ))
        await conn.execute(IrrelevantTrial.__table__.insert().values(
            nct_id="NCT50000005", brief_title="U rejected", ai_relevance_label="unsure",
            phase="PHASE1", rejected_by="admin@local",
        ))
        await conn.execute(ClinicalTrial.__table__.insert().values(
            nct_id="NCT50000006", brief_title="U pending", status=TrialStatus.PENDING_REVIEW,
            ai_relevance_label="unsure",
        ))

    r = await test_client.get("/api/v1/trials/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["confident_error_rate"] == pytest.approx(1 / 3)
    assert body["unsure_approval_rate"] == pytest.approx(1 / 2)
    assert body["unsure_pending"] == 1
    assert len(body["confident_false_positives"]) == 1
    assert body["confident_false_positives"][0]["reviewer_notes"] == "Not actually relevant"

    phase_buckets = [
        p for p in body["unsure_patterns"] if p["dimension"] == "phase" and p["value"] == "PHASE1"
    ]
    assert phase_buckets == [{"dimension": "phase", "value": "PHASE1", "approved": 1, "rejected": 1}]


@pytest.mark.asyncio
async def test_restore_preserves_ai_label_and_enables_fn_detection(test_client, db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(IrrelevantTrial.__table__.insert().values(
            nct_id="NCT50000010", brief_title="AI-rejected trial",
            ai_relevance_label="reject", ai_relevance_reason="Looked irrelevant",
            rejected_by=None,
        ))

    # Restore should carry the AI verdict back onto the clinical trial
    r = await test_client.post("/api/v1/irrelevant-trials/NCT50000010/restore")
    assert r.status_code == 200
    assert r.json()["ai_relevance_label"] == "reject"

    # Approving the restored AI-rejected trial makes it a false negative
    r = await test_client.patch("/api/v1/trials/NCT50000010/approve", json={"username": "admin"})
    assert r.status_code == 200

    r = await test_client.get("/api/v1/trials/insights")
    body = r.json()
    assert body["false_negative_count"] == 1
    assert body["false_negatives"][0]["nct_id"] == "NCT50000010"


# ── POST /trials/insights/ai-advice ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_advice_returns_not_enough_data_when_empty(test_client):
    r = await test_client.post("/api/v1/trials/insights/ai-advice")
    assert r.status_code == 200
    body = r.json()
    assert "Not enough" in body["summary"]
    assert body["patterns"] == []


@pytest.mark.asyncio
async def test_ai_advice_uses_llm_when_data_present(test_client, db_engine, monkeypatch):
    from app.services.ai.schemas import AccuracyAdvice

    class _FakeAIClient:
        def __init__(self, *args, **kwargs):
            pass

        async def analyze_accuracy(self, system_prompt, user_prompt):
            return AccuracyAdvice(
                summary="Confident trials are reliable.",
                patterns=["Soft-tissue sarcomas often slip through as unsure"],
                recommendations=["Clarify bone-sarcoma eligibility in the prompt"],
            )

    monkeypatch.setattr("app.api.endpoints.AIClient", _FakeAIClient)

    async with db_engine.begin() as conn:
        await conn.execute(IrrelevantTrial.__table__.insert().values(
            nct_id="NCT50000020", brief_title="Confident but rejected",
            ai_relevance_label="confident", rejected_by="admin@local",
            reviewer_notes="Wrong cancer type",
        ))

    r = await test_client.post("/api/v1/trials/insights/ai-advice")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == "Confident trials are reliable."
    assert body["patterns"] == ["Soft-tissue sarcomas often slip through as unsure"]
    assert body["recommendations"] == ["Clarify bone-sarcoma eligibility in the prompt"]
