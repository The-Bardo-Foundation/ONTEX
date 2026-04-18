import logging

from app.core.config import settings

from .client import AIClient
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT_TEMPLATE
from .schemas import ClassificationResult, RelevanceTier

logger = logging.getLogger(__name__)


async def classify_trial(
    client: AIClient,
    trial: dict,
) -> ClassificationResult:
    """Classify a trial dict for osteosarcoma relevance.

    Args:
        client: Configured AIClient instance (shared across ingestion run).
        trial: Flat dict from map_api_to_model() (official_* fields populated).

    Returns:
        ClassificationResult. If the LLM is uncertain and marks the trial as
        irrelevant with confidence below CONFIDENCE_THRESHOLD, the result is
        overridden to is_relevant=True so the editorial team can make the final
        call. The AIClient itself already returns a safe is_relevant=True default
        on hard failures, so this function always returns a usable result.
    """
    nct_id = trial.get("nct_id")

    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        nct_id=nct_id,
        brief_title=trial.get("brief_title") or "Not provided",
        brief_summary=trial.get("brief_summary") or "Not provided",
        study_type=trial.get("study_type") or "Not provided",
        phase=trial.get("phase") or "Not provided",
        overall_status=trial.get("overall_status") or "Not provided",
        eligibility_criteria=trial.get("eligibility_criteria") or "Not provided",
        intervention_description=trial.get("intervention_description") or "Not provided",
    )

    result = await client.classify_trial(
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # Safety override: low-confidence irrelevant → include for human review.
    # Osteosarcoma is rare — missing a relevant trial is worse than a false positive.
    if not result.is_relevant and result.confidence < settings.CONFIDENCE_THRESHOLD:
        logger.info(
            "Overriding low-confidence irrelevant for %s (confidence=%.2f)",
            nct_id,
            result.confidence,
        )
        criteria = list(result.matching_criteria)
        if "low_confidence_override" not in criteria:
            criteria.append("low_confidence_override")

        result = result.model_copy(
            update={
                "is_relevant": True,
                "reason": (
                    f"Low confidence ({result.confidence:.0%}) — included for human review. "
                    f"Original: {result.reason}"
                ),
                "relevance_tier": RelevanceTier.SECONDARY,
                "matching_criteria": criteria,
            }
        )

    return result
