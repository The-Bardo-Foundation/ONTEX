"""
Unit tests for AI services: summarizer, classifier, and AIClient.

All LLM calls are replaced by AsyncMock — no real OpenAI API calls are made.
pytest_configure in conftest.py sets OPENROUTER_API_KEY to a dummy value so
AIClient.__init__ doesn't raise before we can mock _client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ai.schemas import ClassificationResult, ConfidenceLabel, RelevanceTier


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
        label=ConfidenceLabel.CONFIDENT,
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
async def test_classify_trial_confident_returned_unchanged():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(label=ConfidenceLabel.CONFIDENT, relevance_tier=RelevanceTier.PRIMARY)
    )

    result = await classify_trial(mock_client, _trial())

    assert result.label == ConfidenceLabel.CONFIDENT
    assert result.relevance_tier == RelevanceTier.PRIMARY


@pytest.mark.asyncio
async def test_classify_trial_reject_returned_unchanged():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            label=ConfidenceLabel.REJECT,
            relevance_tier=RelevanceTier.IRRELEVANT,
            matching_criteria=["none"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    assert result.label == ConfidenceLabel.REJECT
    assert result.relevance_tier == RelevanceTier.IRRELEVANT


@pytest.mark.asyncio
async def test_classify_trial_unsure_goes_to_review():
    from app.services.ai.classifier import classify_trial

    mock_client = MagicMock()
    mock_client.classify_trial = AsyncMock(
        return_value=_classification(
            label=ConfidenceLabel.UNSURE,
            reason="uncertain eligibility",
            relevance_tier=RelevanceTier.SECONDARY,
            matching_criteria=["none"],
        )
    )

    result = await classify_trial(mock_client, _trial())

    assert result.label == ConfidenceLabel.UNSURE
    assert result.relevance_tier == RelevanceTier.SECONDARY


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
        '{"label": "confident", "reason": "osteosarcoma",'
        ' "relevance_tier": "primary", "matching_criteria": ["osteosarcoma_in_conditions"]}'
    )
    ai_client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await ai_client.classify_trial("sys", "user")

    assert result.label == ConfidenceLabel.CONFIDENT
    assert result.relevance_tier == RelevanceTier.PRIMARY


@pytest.mark.asyncio
async def test_ai_client_classify_trial_returns_safe_default_on_failure(ai_client):
    ai_client._client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("API down")
    )

    result = await ai_client.classify_trial("sys", "user", max_retries=0)

    assert isinstance(result, ClassificationResult)
    assert result.label == ConfidenceLabel.UNSURE
    assert "needs manual review" in result.reason
