"""
AI summarisation — generates patient-friendly custom_* fields for a trial.

Public API:
  ai_generate_summaries(client, trial_data) → dict of custom_* field values

On LLM failure, all custom_* fields are returned as None so the admin can fill
them in manually via the dashboard. This function never raises.
"""

import logging

from .client import AIClient
from .prompts import SUMMARIZATION_SYSTEM_PROMPT, SUMMARIZATION_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# The six custom_* fields this function is responsible for generating.
# Remaining custom_* fields (location, contact, age, date) are left None —
# they are either passthroughs or filled in manually by admins.
_GENERATED_FIELDS = [
    "custom_brief_title",
    "custom_brief_summary",
    "custom_overall_status",
    "custom_eligibility_criteria",
    "custom_intervention_description",
    "key_information",
]

_NULL_RESULT = {field: None for field in _GENERATED_FIELDS}


async def ai_generate_summaries(client: AIClient, trial_data: dict) -> dict:
    """Generate patient-friendly summary fields for a trial using the LLM.

    Args:
        client: Configured AIClient instance (shared across ingestion run).
        trial_data: Flat dict from map_api_to_model() with official_* fields.

    Returns:
        Dict with keys from _GENERATED_FIELDS. Values are strings from the LLM
        or None if the LLM failed or returned no value for that field.
        Never raises.
    """
    nct_id = trial_data.get("nct_id", "unknown")

    user_prompt = SUMMARIZATION_USER_PROMPT_TEMPLATE.format(
        nct_id=nct_id,
        brief_title=trial_data.get("brief_title") or "Not provided",
        brief_summary=trial_data.get("brief_summary") or "Not provided",
        overall_status=trial_data.get("overall_status") or "Not provided",
        phase=trial_data.get("phase") or "Not provided",
        study_type=trial_data.get("study_type") or "Not provided",
        eligibility_criteria=trial_data.get("eligibility_criteria") or "Not provided",
        intervention_description=trial_data.get("intervention_description") or "Not provided",
    )

    result = await client.generate_summaries(
        system_prompt=SUMMARIZATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    if result is None:
        logger.warning("Summarisation failed for %s — custom_* fields set to None", nct_id)
        return _NULL_RESULT.copy()

    return {field: result.get(field) for field in _GENERATED_FIELDS}
