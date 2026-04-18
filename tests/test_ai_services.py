"""
Unit tests for AI services: summarizer, classifier, and AIClient.

All LLM calls are replaced by AsyncMock — no real OpenAI API calls are made.
pytest_configure in conftest.py sets OPENAI_API_KEY to a dummy value so
AIClient.__init__ doesn't raise before we can mock _client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ai.schemas import ClassificationResult, RelevanceTier


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _trial():
    return {
        "nct_id": "NCT00000001",
        "brief_title": "An Osteosarcoma Trial",
        "brief_summary": "A trial for osteosarcoma patients.",
        "overall_status": "RECRUITING",
        "phase": "Phase 2",
        "study_type": "INTERVENTIONAL",
        "eligibility_criteria": "Osteosarcoma diagnosis required.",
        "intervention_description": "Drug: TestDrug",
    }


def _classification(**kwargs) -> ClassificationResult:
    defaults = dict(
        is_relevant=True,
        confidence=0.9,
        reason="osteosarcoma mentioned",
        relevance_tier=RelevanceTier.PRIMARY,
        matching_criteria=["osteosarcoma_in_conditions"],
    )
    defaults.update(kwargs)
    return ClassificationResult(**defaults)


@pytest.fixture
def ai_client():
    """AIClient with a dummy key; _client replaced so no real HTTP is attempted."""
    from app.services.ai.client import AIClient

    client = AIClient(api_key="sk-test-not-real")
    client._client = MagicMock()
    return client


# ─── Section A: ai_generate_summaries (summarizer.py) ────────────────────────


@pytest.mark.asyncio
async def test_ai_generate_summaries_returns_summary_on_success():
    from app.services.ai.summarizer import ai_generate_summaries

    mock_client = MagicMock()
    mock_client.generate_summaries = AsyncMock(
        return_value={"custom_brief_summary": "Patient-friendly text."}
    )

    result = await ai_generate_summaries(mock_client, _trial())

    assert result == {"custom_brief_summary": "Patient-friendly text."}


@pytest.mark.asyncio
async def test_ai_generate_summaries_returns_null_dict_when_llm_returns_none():
    from app.services.ai.summarizer import ai_generate_summaries

    mock_client = MagicMock()
    mock_client.generate_summaries = AsyncMock(return_value=None)

    result = await ai_generate_summaries(mock_client, _trial())

    assert result == {"custom_brief_summary": None}


@pytest.mark.asyncio
async def test_ai_generate_summaries_ignores_extra_keys_from_llm():
    from app.services.ai.summarizer import ai_generate_summaries

    mock_client = MagicMock()
    mock_client.generate_summaries = AsyncMock(
        return_value={"custom_brief_summary": "text", "extra_key": "ignored"}
    )

    result = await ai_generate_summaries(mock_client, _trial())

    assert "extra_key" not in result
    assert result == {"custom_brief_summary": "text"}


# ─── Section B: classify_trial (classifier.py) ───────────────────────────────


@pytest.mark.asyncio
async def test_classify_trial_relevant_high_confidence_returned_unchanged():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(is_relevant=True, confidence=0.95, relevance_tier=RelevanceTier.PRIMARY)
    )

    result = await classify_trial(mock_client, _trial())

    assert result.is_relevant is True
    assert result.relevance_tier == RelevanceTier.PRIMARY


@pytest.mark.asyncio
async def test_classify_trial_irrelevant_high_confidence_stays_irrelevant():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            is_relevant=False,
            confidence=0.92,
            relevance_tier=RelevanceTier.IRRELEVANT,
            matching_criteria=["none"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    # 0.92 >= 0.7 (default threshold) — no override
    assert result.is_relevant is False
    assert result.relevance_tier == RelevanceTier.IRRELEVANT


@pytest.mark.asyncio
async def test_classify_trial_irrelevant_low_confidence_flipped_to_relevant():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            is_relevant=False,
            confidence=0.55,
            reason="uncertain",
            relevance_tier=RelevanceTier.IRRELEVANT,
            matching_criteria=["none"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    # 0.55 < 0.7 → safety override
    assert result.is_relevant is True
    assert result.relevance_tier == RelevanceTier.SECONDARY
    assert "low_confidence_override" in result.matching_criteria
    assert "Low confidence" in result.reason
    assert "uncertain" in result.reason  # original reason preserved


@pytest.mark.asyncio
async def test_classify_trial_low_confidence_override_appended_once():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            is_relevant=False,
            confidence=0.55,
            relevance_tier=RelevanceTier.IRRELEVANT,
            # already contains the tag — must not be duplicated
            matching_criteria=["none", "low_confidence_override"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    assert result.matching_criteria.count("low_confidence_override") == 1


@pytest.mark.asyncio
async def test_classify_trial_confidence_threshold_respected_from_settings(monkeypatch):
    import app.services.ai.classifier as classifier_module
    from app.services.ai.classifier import classify_trial

    monkeypatch.setattr(classifier_module.settings, "CONFIDENCE_THRESHOLD", 0.9)

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            is_relevant=False,
            confidence=0.80,
            relevance_tier=RelevanceTier.IRRELEVANT,
            matching_criteria=["none"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    # 0.80 < patched threshold 0.9 → override fires
    assert result.is_relevant is True


# ─── Section C: AIClient fail-safe behavior (client.py) ──────────────────────


@pytest.mark.asyncio
async def test_ai_client_generate_summaries_parses_json_on_success(ai_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"custom_brief_summary": "text"}'
    ai_client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await ai_client.generate_summaries("sys", "user")

    assert result == {"custom_brief_summary": "text"}


@pytest.mark.asyncio
async def test_ai_client_generate_summaries_returns_none_on_all_retries_exhausted(ai_client):
    ai_client._client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("API down")
    )

    result = await ai_client.generate_summaries("sys", "user", max_retries=0)

    assert result is None


@pytest.mark.asyncio
async def test_ai_client_classify_trial_parses_json_on_success(ai_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '{"is_relevant": true, "confidence": 0.9, "reason": "osteosarcoma",'
        ' "relevance_tier": "primary", "matching_criteria": ["osteosarcoma_in_conditions"]}'
    )
    ai_client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await ai_client.classify_trial("sys", "user")

    assert result.is_relevant is True
    assert result.relevance_tier == RelevanceTier.PRIMARY


@pytest.mark.asyncio
async def test_ai_client_classify_trial_returns_safe_default_on_failure(ai_client):
    ai_client._client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("API down")
    )

    result = await ai_client.classify_trial("sys", "user", max_retries=0)

    assert isinstance(result, ClassificationResult)
    assert result.is_relevant is True
    assert result.confidence == 0.0
    assert "needs manual review" in result.reason
