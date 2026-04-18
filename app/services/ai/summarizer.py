"""
AI summarisation — generates a patient-friendly custom_brief_summary for a trial.

Public API:
  ai_generate_summaries(client, trial_data) → dict with custom_brief_summary value

All other custom_* fields are passthroughs from the ClinicalTrials.gov API data
(populated by map_api_to_model). Only custom_brief_summary is AI-generated.

On LLM failure, custom_brief_summary is returned as None so the admin can fill
it in manually via the dashboard. This function never raises.
"""

import logging

from .client import AIClient
from .prompts import SUMMARIZATION_SYSTEM_PROMPT, SUMMARIZATION_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Only custom_brief_summary is AI-generated. All other custom_* fields are
# passthroughs from the ClinicalTrials.gov API data set in map_api_to_model.
_GENERATED_FIELDS = [
    "custom_brief_summary",
]

_NULL_RESULT = {field: None for field in _GENERATED_FIELDS}


async def ai_generate_summaries(client: AIClient, trial_data: dict) -> dict:
    """Generate a patient-friendly summary for a trial using the LLM.

    Args:
        client: Configured AIClient instance (shared across ingestion run).
        trial_data: Flat dict from map_api_to_model() with official fields.

    Returns:
        Dict with key "custom_brief_summary". Value is a string from the LLM
        or None if the LLM failed or returned no value.
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
        logger.warning(
            "Summarisation failed for %s — custom_brief_summary set to None "
            "(see preceding generate_summaries error log for details)",
            nct_id,
        )
        return _NULL_RESULT.copy()

    return {field: result.get(field) for field in _GENERATED_FIELDS}
