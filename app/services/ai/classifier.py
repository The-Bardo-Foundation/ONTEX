import logging

from .client import AIClient
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT_TEMPLATE
from .schemas import ClassificationResult

logger = logging.getLogger(__name__)


async def classify_trial(
    client: AIClient,
    trial: dict,
) -> ClassificationResult:
    """Classify a trial dict for osteosarcoma relevance.

    Returns ClassificationResult with label "confident", "unsure", or "reject".
    The AIClient returns a safe "unsure" default on hard failures, so this
    function always returns a usable result.
    """
    user_prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        nct_id=trial.get("nct_id"),
        brief_title=trial.get("brief_title") or "Not provided",
        brief_summary=trial.get("brief_summary") or "Not provided",
        study_type=trial.get("study_type") or "Not provided",
        phase=trial.get("phase") or "Not provided",
        overall_status=trial.get("overall_status") or "Not provided",
        eligibility_criteria=trial.get("eligibility_criteria") or "Not provided",
        intervention_description=trial.get("intervention_description") or "Not provided",
    )

    return await client.classify_trial(
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
