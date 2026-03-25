import logging

from .client import AIClient
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT_TEMPLATE
from .schemas import ClassificationResult

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7


async def classify_trial(
    client: AIClient,
    trial,  # TODO: type this when input is decided (e.g. ClinicalTrial from db/models.py)
) -> ClassificationResult:

    # TODO: get nct_id from trial object
    nct_id = None

    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        nct_id=nct_id,                      # TODO: from trial
        brief_title=None,                   # TODO: from trial
        brief_summary=None,                 # TODO: from trial
        study_type=None,                    # TODO: from trial
        phase=None,                         # TODO: from trial
        overall_status=None,                # TODO: from trial
        eligibility_criteria=None,          # TODO: from trial
        intervention_description=None,      # TODO: from trial
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
