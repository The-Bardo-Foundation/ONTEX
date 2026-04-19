"""
Unit tests for the ingestion pipeline (app/services/ingestion.py).

Covers:
- New trial: classified relevant → stored as PENDING_REVIEW in clinical_trials
- New trial: classified irrelevant → stored in irrelevant_trials
- Updated trial (date changed): re-processed, status reset to PENDING_REVIEW
- Rejected trial re-evaluated when date changed: moved to clinical_trials
- Rejected trial with same date: not re-evaluated (skipped)
- Trial in clinical_trials reclassified as irrelevant: row removed from clinical_trials
- Trial in irrelevant_trials reclassified as relevant: row removed from irrelevant_trials
- Missing nct_id from map_api_to_model: trial skipped
- Missing brief_title from API: map_api_to_model uses safe fallback
- AI summarisation failure: custom_* fields remain None, trial still processed
- AI classification failure: safe default (label=unsure, PENDING_REVIEW)
- Admin-edited custom_* fields preserved on re-ingestion
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.db.database import Base
from app.db.models import ClinicalTrial, IngestionEvent, IrrelevantTrial, TrialStatus
from app.services.ai.schemas import ClassificationResult, ConfidenceLabel
from app.services.ctgov.study_detail import map_api_to_model


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_classification(
    label: ConfidenceLabel = ConfidenceLabel.CONFIDENT,
    reason: str = "osteosarcoma mentioned",
) -> ClassificationResult:
    return ClassificationResult(
        label=label,
        reason=reason,
        matching_criteria=["osteosarcoma_in_conditions"],
    )


def make_trial_dict(
    nct_id: str = "NCT11111111",
    brief_title: str = "Test Osteosarcoma Trial",
    last_update: str = "2024-06-01",
) -> dict:
    """Return a fully-populated trial dict as produced by map_api_to_model."""
    return {
        "nct_id": nct_id,
        "brief_title": brief_title,
        "brief_summary": "A trial testing a drug for osteosarcoma.",
        "overall_status": "RECRUITING",
        "phase": "Phase 2",
        "study_type": "INTERVENTIONAL",
        "location_country": "Norway",
        "location_city": "Oslo",
        "minimum_age": "5 Years",
        "maximum_age": "25 Years",
        "central_contact_name": None,
        "central_contact_phone": None,
        "central_contact_email": None,
        "eligibility_criteria": "Inclusion: osteosarcoma diagnosis",
        "intervention_description": "Drug: TestDrug",
        "last_update_post_date": last_update,
        # custom_* fields: passthroughs from official data except custom_brief_summary
        "custom_brief_title": brief_title,
        "custom_brief_summary": None,
        "custom_overall_status": "RECRUITING",
        "custom_phase": "Phase 2",
        "custom_study_type": "INTERVENTIONAL",
        "custom_location_country": "Norway",
        "custom_location_city": "Oslo",
        "custom_minimum_age": "5 Years",
        "custom_maximum_age": "25 Years",
        "custom_central_contact_name": None,
        "custom_central_contact_phone": None,
        "custom_central_contact_email": None,
        "custom_eligibility_criteria": "Inclusion: osteosarcoma diagnosis",
        "custom_intervention_description": "Drug: TestDrug",
        "custom_last_update_post_date": last_update,
        "key_information": None,
    }


FAKE_AI_SUMMARIES = {
    "custom_brief_summary": "AI-generated summary",
}

NULL_AI_SUMMARIES = {field: None for field in FAKE_AI_SUMMARIES}


# ─── DB fixture helpers ───────────────────────────────────────────────────────

def _make_test_db(tmp_path, name: str = "test.db"):
    """Create an async SQLite engine + session factory with test tables."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / name}", echo=False
    )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def _make_mock_ai_client(
    summaries: dict | None = None,
    classification: ClassificationResult | None = None,
) -> MagicMock:
    """Return a mock AIClient with controllable generate_summaries/classify_trial."""
    client = MagicMock()
    client.generate_summaries = AsyncMock(
        return_value=summaries if summaries is not None else FAKE_AI_SUMMARIES
    )
    client.classify_trial = AsyncMock(
        return_value=classification or make_classification()
    )
    return client


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_relevant_trial_stored_as_pending_review(tmp_path, monkeypatch):
    """A brand-new relevant trial should be stored in clinical_trials as PENDING_REVIEW."""
    engine, factory = _make_test_db(tmp_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    trial_dict = make_trial_dict()
    mock_client = _make_mock_ai_client()

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT11111111", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: mock_client)
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT11111111")
        assert trial is not None
        assert trial.status == TrialStatus.PENDING_REVIEW
        assert trial.brief_title == "Test Osteosarcoma Trial"
        assert trial.custom_brief_summary == "AI-generated summary"
        # custom_brief_title is a passthrough from the API, not AI-generated
        assert trial.custom_brief_title == "Test Osteosarcoma Trial"

    await engine.dispose()


@pytest.mark.asyncio
async def test_new_irrelevant_trial_stored_in_irrelevant_table(tmp_path, monkeypatch):
    """A brand-new trial classified as irrelevant should go into irrelevant_trials only."""
    engine, factory = _make_test_db(tmp_path, "test2.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    trial_dict = make_trial_dict(nct_id="NCT22222222")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT22222222", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification(label=ConfidenceLabel.REJECT)),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        irrelevant = await db.get(IrrelevantTrial, "NCT22222222")
        assert irrelevant is not None
        clinical = await db.get(ClinicalTrial, "NCT22222222")
        assert clinical is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_updated_trial_resets_status_to_pending_review(tmp_path, monkeypatch):
    """An APPROVED trial whose date changed on ClinicalTrials.gov should be re-processed
    and its status reset to PENDING_REVIEW."""
    engine, factory = _make_test_db(tmp_path, "test3.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-populate an APPROVED trial with old date
    async with factory() as db:
        existing = ClinicalTrial(
            nct_id="NCT33333333",
            brief_title="Old Title",
            last_update_post_date="2024-01-01",
            status=TrialStatus.APPROVED,
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT33333333", last_update="2024-09-01")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        # API reports a newer date
        lambda **kwargs: [("NCT33333333", "2024-09-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT33333333")
        assert trial is not None
        assert trial.status == TrialStatus.PENDING_REVIEW
        assert trial.last_update_post_date == "2024-09-01"

    await engine.dispose()


@pytest.mark.asyncio
async def test_rejected_trial_reeval_moved_to_clinical_trials(tmp_path, monkeypatch):
    """An IrrelevantTrial whose date changed should be re-evaluated; if now relevant,
    it moves to clinical_trials and is removed from irrelevant_trials."""
    engine, factory = _make_test_db(tmp_path, "test4.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as db:
        existing = IrrelevantTrial(
            nct_id="NCT44444444",
            brief_title="Old Irrelevant Trial",
            last_update_post_date="2024-01-01",
            irrelevance_reason="Not osteosarcoma-related",
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT44444444", last_update="2024-10-01")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT44444444", "2024-10-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        clinical = await db.get(ClinicalTrial, "NCT44444444")
        assert clinical is not None
        assert clinical.status == TrialStatus.PENDING_REVIEW
        irrelevant = await db.get(IrrelevantTrial, "NCT44444444")
        assert irrelevant is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_rejected_trial_same_date_not_reevaluated(tmp_path, monkeypatch):
    """An IrrelevantTrial whose date has NOT changed should not be re-evaluated."""
    engine, factory = _make_test_db(tmp_path, "test5.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as db:
        existing = IrrelevantTrial(
            nct_id="NCT55555555",
            brief_title="Still Irrelevant",
            last_update_post_date="2024-01-01",
            irrelevance_reason="Not relevant",
        )
        db.add(existing)
        await db.commit()

    fetch_called = {"count": 0}

    def track_fetch(nct_id):
        fetch_called["count"] += 1
        return {"protocolSection": {}}

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        # Same date as in DB
        lambda **kwargs: [("NCT55555555", "2024-01-01")],
    )
    monkeypatch.setattr("app.services.ingestion.fetch_full_study", track_fetch)
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    # fetch_full_study should never be called since no re-evaluation is needed
    assert fetch_called["count"] == 0

    async with factory() as db:
        irrelevant = await db.get(IrrelevantTrial, "NCT55555555")
        assert irrelevant is not None
        clinical = await db.get(ClinicalTrial, "NCT55555555")
        assert clinical is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_clinical_trial_reclassified_irrelevant_removes_clinical_row(tmp_path, monkeypatch):
    """A ClinicalTrial reclassified as irrelevant should be removed from clinical_trials
    and stored in irrelevant_trials."""
    engine, factory = _make_test_db(tmp_path, "test6.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as db:
        existing = ClinicalTrial(
            nct_id="NCT66666666",
            brief_title="Previously Relevant Trial",
            last_update_post_date="2024-01-01",
            status=TrialStatus.APPROVED,
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT66666666", last_update="2024-11-01")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT66666666", "2024-11-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification(label=ConfidenceLabel.REJECT)),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        clinical = await db.get(ClinicalTrial, "NCT66666666")
        assert clinical is None
        irrelevant = await db.get(IrrelevantTrial, "NCT66666666")
        assert irrelevant is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_missing_nct_id_trial_is_skipped(tmp_path, monkeypatch):
    """If map_api_to_model returns a dict with no nct_id, the trial should be silently skipped."""
    engine, factory = _make_test_db(tmp_path, "test7.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bad_trial = make_trial_dict()
    bad_trial["nct_id"] = None  # simulate missing nct_id from API

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT77777777", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: bad_trial.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    # Should complete without raising, and nothing gets stored
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        from sqlalchemy import select
        ct_rows = (await db.execute(select(ClinicalTrial))).scalars().all()
        it_rows = (await db.execute(select(IrrelevantTrial))).scalars().all()
        assert len(ct_rows) == 0
        assert len(it_rows) == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_ai_summarisation_failure_trial_still_processed(tmp_path, monkeypatch):
    """If AI summarisation fails (returns None), custom_* fields stay None but the trial
    is still classified and stored."""
    engine, factory = _make_test_db(tmp_path, "test8.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    trial_dict = make_trial_dict(nct_id="NCT88888888")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT88888888", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    # Summarisation fails → returns all-None dict
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=NULL_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT88888888")
        assert trial is not None
        assert trial.status == TrialStatus.PENDING_REVIEW
        # custom_brief_title is a passthrough, so it should have the API value
        assert trial.custom_brief_title == "Test Osteosarcoma Trial"
        # custom_brief_summary is AI-generated, so it should be None on failure
        assert trial.custom_brief_summary is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_ai_classification_failure_defaults_to_unsure(tmp_path, monkeypatch):
    """If classify_trial raises an exception, the trial should default to unsure
    so no trial is silently lost."""
    engine, factory = _make_test_db(tmp_path, "test9.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    trial_dict = make_trial_dict(nct_id="NCT99999999")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT99999999", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    # Classification raises an unexpected exception
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(side_effect=RuntimeError("OpenAI timeout")),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT99999999")
        assert trial is not None
        assert trial.status == TrialStatus.PENDING_REVIEW
        assert trial.ai_relevance_label == "unsure"

    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_edited_custom_fields_preserved_on_update(tmp_path, monkeypatch):
    """On re-ingestion of an updated trial, any non-null custom_* fields already in the
    DB (i.e., admin-edited values) should NOT be overwritten by AI-generated content."""
    engine, factory = _make_test_db(tmp_path, "test10.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    admin_summary = "Admin-curated patient-friendly summary"

    async with factory() as db:
        existing = ClinicalTrial(
            nct_id="NCT10101010",
            brief_title="Original Title",
            last_update_post_date="2024-01-01",
            status=TrialStatus.APPROVED,
            custom_brief_summary=admin_summary,  # admin has edited this field
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT10101010", last_update="2024-12-01")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT10101010", "2024-12-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        # AI would overwrite with a different value
        AsyncMock(return_value={**FAKE_AI_SUMMARIES, "custom_brief_summary": "AI-generated summary"}),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT10101010")
        assert trial is not None
        # Admin-edited field must be preserved
        assert trial.custom_brief_summary == admin_summary
        # custom_brief_title is a passthrough from the API, not AI-generated
        assert trial.custom_brief_title == "Test Osteosarcoma Trial"

    await engine.dispose()


# ─── map_api_to_model unit tests ─────────────────────────────────────────────

def test_map_api_to_model_missing_brief_title_uses_fallback():
    """map_api_to_model should use a safe placeholder when briefTitle is absent,
    preventing a NOT NULL constraint violation on the DB column."""
    raw = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000001",
                # briefTitle deliberately absent
            }
        }
    }
    result = map_api_to_model(raw)
    assert result["nct_id"] == "NCT00000001"
    assert result["brief_title"] == "Title not available"


def test_map_api_to_model_passthroughs_and_none_fields():
    """custom_brief_summary and key_information should be None; other custom_* fields
    should be passthroughs from their corresponding official API fields."""
    raw = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000002",
                "briefTitle": "A real title",
            }
        }
    }
    result = map_api_to_model(raw)
    # These two should always be None (AI-generated / admin-filled)
    assert result["custom_brief_summary"] is None
    assert result["key_information"] is None
    # custom_brief_title should match brief_title
    assert result["custom_brief_title"] == result["brief_title"]
    # Other passthrough fields should match their official counterparts
    assert result["custom_overall_status"] == result["overall_status"]
    assert result["custom_phase"] == result["phase"]
    assert result["custom_study_type"] == result["study_type"]
    assert result["custom_location_country"] == result["location_country"]
    assert result["custom_location_city"] == result["location_city"]
    assert result["custom_minimum_age"] == result["minimum_age"]
    assert result["custom_maximum_age"] == result["maximum_age"]
    assert result["custom_central_contact_name"] == result["central_contact_name"]
    assert result["custom_central_contact_phone"] == result["central_contact_phone"]
    assert result["custom_central_contact_email"] == result["central_contact_email"]
    assert result["custom_eligibility_criteria"] == result["eligibility_criteria"]
    assert result["custom_intervention_description"] == result["intervention_description"]
    assert result["custom_last_update_post_date"] == result["last_update_post_date"]


def test_map_api_to_model_extracts_interventions():
    """Interventions should be joined as 'Type: Name (Description)' lines."""
    raw = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000003", "briefTitle": "T"},
            "armsInterventionsModule": {
                "interventions": [
                    {"type": "DRUG", "name": "Ifosfamide", "description": "Chemo agent"},
                    {"type": "DRUG", "name": "Cisplatin", "description": ""},
                ]
            },
        }
    }
    result = map_api_to_model(raw)
    assert "DRUG: Ifosfamide (Chemo agent)" in result["intervention_description"]
    assert "DRUG: Cisplatin" in result["intervention_description"]


def test_map_api_to_model_deduplicates_locations():
    """Duplicate countries/cities in location list should be deduplicated."""
    raw = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000004", "briefTitle": "T"},
            "contactsLocationsModule": {
                "locations": [
                    {"country": "Norway", "city": "Oslo"},
                    {"country": "Norway", "city": "Bergen"},
                    {"country": "Norway", "city": "Oslo"},  # duplicate
                ]
            },
        }
    }
    result = map_api_to_model(raw)
    countries = result["location_country"].split(", ")
    assert countries.count("Norway") == 1
    cities = result["location_city"].split(", ")
    assert cities.count("Oslo") == 1


# ─── ingestion_event and previous_official_snapshot tests ────────────────────

@pytest.mark.asyncio
async def test_new_trial_has_ingestion_event_new(tmp_path, monkeypatch):
    """A brand-new trial should have ingestion_event=NEW after ingestion."""
    engine, factory = _make_test_db(tmp_path, "test_event_new.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    trial_dict = make_trial_dict(nct_id="NCT_NEW_EVENT")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT_NEW_EVENT", "2024-06-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT_NEW_EVENT")
        assert trial is not None
        assert trial.ingestion_event == IngestionEvent.NEW

    await engine.dispose()


@pytest.mark.asyncio
async def test_updated_trial_has_ingestion_event_updated(tmp_path, monkeypatch):
    """A trial already in the DB with a new last_update_post_date should have
    ingestion_event=UPDATED after re-ingestion."""
    engine, factory = _make_test_db(tmp_path, "test_event_updated.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-populate trial with an old date
    async with factory() as db:
        existing = ClinicalTrial(
            nct_id="NCT_UPD_EVENT",
            brief_title="Old Title",
            last_update_post_date="2024-01-01",
            status=TrialStatus.PENDING_REVIEW,
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT_UPD_EVENT", last_update="2024-12-01")

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT_UPD_EVENT", "2024-12-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT_UPD_EVENT")
        assert trial is not None
        assert trial.ingestion_event == IngestionEvent.UPDATED

    await engine.dispose()


@pytest.mark.asyncio
async def test_approved_trial_update_saves_previous_official_snapshot(tmp_path, monkeypatch):
    """When an APPROVED trial is re-ingested with a new date, previous_official_snapshot
    should contain the official fields as they were before the re-ingestion."""
    engine, factory = _make_test_db(tmp_path, "test_snapshot.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    old_summary = "The original brief summary from ClinicalTrials.gov"

    async with factory() as db:
        existing = ClinicalTrial(
            nct_id="NCT_SNAP",
            brief_title="Snapshot Trial",
            brief_summary=old_summary,
            last_update_post_date="2024-01-01",
            status=TrialStatus.APPROVED,
            approved_at=__import__("datetime").datetime(2024, 3, 1),
            approved_by="admin",
        )
        db.add(existing)
        await db.commit()

    trial_dict = make_trial_dict(nct_id="NCT_SNAP", last_update="2024-12-01")
    trial_dict["brief_summary"] = "Updated summary from ClinicalTrials.gov"

    monkeypatch.setattr("app.services.ingestion.SessionLocal", factory)
    monkeypatch.setattr(
        "app.services.ingestion.iter_study_index_rows",
        lambda **kwargs: [("NCT_SNAP", "2024-12-01")],
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_full_study",
        lambda nct_id: {"protocolSection": {}},
    )
    monkeypatch.setattr(
        "app.services.ingestion.map_api_to_model",
        lambda raw: trial_dict.copy(),
    )
    monkeypatch.setattr("app.services.ingestion.AIClient", lambda: _make_mock_ai_client())
    monkeypatch.setattr(
        "app.services.ingestion.ai_generate_summaries",
        AsyncMock(return_value=FAKE_AI_SUMMARIES),
    )
    monkeypatch.setattr(
        "app.services.ingestion.classify_trial",
        AsyncMock(return_value=make_classification()),
    )

    from app.services.ingestion import run_daily_ingestion
    await run_daily_ingestion(search_terms=["osteosarcoma"])

    async with factory() as db:
        trial = await db.get(ClinicalTrial, "NCT_SNAP")
        assert trial is not None
        assert trial.previous_official_snapshot is not None
        snapshot = json.loads(trial.previous_official_snapshot)
        # Snapshot should contain the OLD brief_summary, not the new one
        assert snapshot["brief_summary"] == old_summary
        # Current brief_summary should be the new value
        assert trial.brief_summary == "Updated summary from ClinicalTrials.gov"

    await engine.dispose()
