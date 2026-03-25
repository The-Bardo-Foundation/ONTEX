import logging


logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7


async def classify_trial(
    client: AIClient,
    trial,
) -> ClassificationResult:
    """Classify a single trial as relevant or irrelevant to osteosarcoma.

    Accepts any object with trial fields (e.g. ClinicalTrial model).
    Applies the 'include rather than exclude' principle:
    if confidence < threshold and is_relevant=False, override to relevant.
    """
    nct_id = getattr(trial, "nct_id", "unknown")

    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        nct_id=nct_id,
        brief_title=getattr(trial, "brief_title", "") or "Not provided",
        brief_summary=getattr(trial, "brief_summary", "") or "Not provided",
        eligibility_criteria=getattr(trial, "eligibility_criteria", "") or "Not provided",
        intervention_description=getattr(trial, "intervention_description", "") or "Not provided",
        study_type=getattr(trial, "study_type", "") or "Not provided",
        phase=getattr(trial, "phase", "") or "Not provided",
        overall_status=getattr(trial, "overall_status", "") or "Not provided",
    )

    result = await client.classify_trial(
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # Safety override: low-confidence irrelevant -> include for human review
    if not result.is_relevant and result.confidence < CONFIDENCE_THRESHOLD:
        logger.info(
            "Overriding low-confidence irrelevant for %s (confidence=%.2f)",
            nct_id,
            result.confidence,
        )
        result.is_relevant = True
        result.reason = (
            f"Low confidence ({result.confidence:.0%}) -- included for human review. "
            f"Original: {result.reason}"
        )

    return result
