"""
ClinicalTrials.gov API v2 — single-study data fetching and field mapping.

Public API:
  fetch_full_study(nct_id)    → raw JSON dict from the API (or None on error)
  map_api_to_model(raw_json)  → flat dict matching ClinicalTrialBase column names

get_trial_data() is kept as a debug/diagnostic helper.
For bulk index fetching see study_index.iter_study_index_rows.
"""

import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


def _get(d: dict, *keys, default=None):
    """Safely navigate a nested dict. Returns default if any key is missing."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is default:
            return default
    return d


def fetch_full_study(nct_id: str) -> dict | None:
    """Fetch the full study JSON for a single trial from ClinicalTrials.gov API v2.

    Synchronous (uses requests). Callers in the async ingestion pipeline should
    wrap this with asyncio.to_thread().

    Args:
        nct_id: NCT identifier, e.g. "NCT04132895".

    Returns:
        Parsed JSON dict on success, or None if the request fails.
    """
    url = f"{_BASE_URL}/{nct_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning("fetch_full_study failed for %s: %s", nct_id, e)
        return None


def map_api_to_model(raw_json: dict) -> dict:
    """Map a raw ClinicalTrials.gov API v2 study JSON to a flat dict matching
    ClinicalTrialBase column names.

    All custom_* fields are set to None here — they are populated by the AI
    summarisation step (ai_generate_summaries) in the ingestion pipeline.

    Args:
        raw_json: The full JSON object returned by fetch_full_study().

    Returns:
        Dict with keys matching every ClinicalTrialBase column.
    """
    protocol = _get(raw_json, "protocolSection") or {}
    ident = _get(protocol, "identificationModule") or {}
    status_mod = _get(protocol, "statusModule") or {}
    design = _get(protocol, "designModule") or {}
    eligibility = _get(protocol, "eligibilityModule") or {}
    contacts_locs = _get(protocol, "contactsLocationsModule") or {}
    arms = _get(protocol, "armsInterventionsModule") or {}
    description = _get(protocol, "descriptionModule") or {}

    # --- Location: deduplicated, comma-joined lists ---
    locations = contacts_locs.get("locations") or []
    countries = list(dict.fromkeys(loc.get("country", "") for loc in locations if loc.get("country")))
    cities = list(dict.fromkeys(loc.get("city", "") for loc in locations if loc.get("city")))

    # --- Central contact (first entry only) ---
    central_contacts = contacts_locs.get("centralContacts") or []
    contact = central_contacts[0] if central_contacts else {}

    # --- Interventions: "Type: Name (Description)" per item, newline-joined ---
    interventions = arms.get("interventions") or []
    intervention_parts = []
    for iv in interventions:
        iv_type = iv.get("type", "")
        iv_name = iv.get("name", "")
        iv_desc = iv.get("description", "")
        part = f"{iv_type}: {iv_name}"
        if iv_desc:
            part += f" ({iv_desc})"
        intervention_parts.append(part)
    intervention_description = "\n".join(intervention_parts) if intervention_parts else None

    # --- Phase: list → comma-joined string ---
    phases = design.get("phases") or []
    phase = ", ".join(phases) if phases else None

    return {
        # Official fields
        "nct_id": _get(ident, "nctId"),
        "brief_title": _get(ident, "briefTitle") or "Title not available",
        "brief_summary": _get(description, "briefSummary"),
        "overall_status": _get(status_mod, "overallStatus"),
        "phase": phase,
        "study_type": _get(design, "studyType"),
        "location_country": ", ".join(countries) if countries else None,
        "location_city": ", ".join(cities) if cities else None,
        "minimum_age": _get(eligibility, "minimumAge"),
        "maximum_age": _get(eligibility, "maximumAge"),
        "central_contact_name": contact.get("name"),
        "central_contact_phone": contact.get("phone"),
        "central_contact_email": contact.get("email"),
        "eligibility_criteria": _get(eligibility, "eligibilityCriteria"),
        "intervention_description": intervention_description,
        "last_update_post_date": _get(status_mod, "lastUpdatePostDateStruct", "date"),
        # custom_* fields are populated by ai_generate_summaries in Step 4
        "custom_brief_title": None,
        "custom_brief_summary": None,
        "custom_overall_status": None,
        "custom_phase": None,
        "custom_study_type": None,
        "custom_location_country": None,
        "custom_location_city": None,
        "custom_minimum_age": None,
        "custom_maximum_age": None,
        "custom_central_contact_name": None,
        "custom_central_contact_phone": None,
        "custom_central_contact_email": None,
        "custom_eligibility_criteria": None,
        "custom_intervention_description": None,
        "custom_last_update_post_date": None,
        "key_information": None,
    }


def get_trial_data(nct_id):
    """
    Fetch a single study from ClinicalTrials.gov and print a human-readable summary.

    Requests a subset of fields from the API v2 single-study endpoint and
    prints the title, status, eligibility criteria, interventions, and contact
    details to stdout.  Intended for local debugging/inspection.

    Args:
        nct_id: The NCT identifier string (e.g. "NCT04132895").
    """

    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"

    # Request only the fields we display so the response payload stays small
    params = {
        "fields": (
            "protocolSection.identificationModule.officialTitle,"
            "protocolSection.statusModule.lastUpdatePostDateStruct,"
            "protocolSection.descriptionModule.briefSummary,"
            "protocolSection.designModule,"
            "protocolSection.statusModule.overallStatus,"
            "protocolSection.eligibilityModule,"
            "protocolSection.contactsLocationsModule,"
            "protocolSection.armsInterventionsModule"
        )
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        study = response.json()

        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        contacts = protocol.get("contactsLocationsModule", {})
        interventions = protocol.get("armsInterventionsModule", {}).get(
            "interventions", []
        )

        # Split the combined eligibility text into inclusion and exclusion sections
        criteria = eligibility.get("eligibilityCriteria", "")
        inclusion = "Not specified"
        exclusion = "Not specified"
        if "Inclusion Criteria:" in criteria and "Exclusion Criteria:" in criteria:
            parts = criteria.split("Exclusion Criteria:")
            inclusion = parts[0].replace("Inclusion Criteria:", "").strip()
            exclusion = parts[1].strip()

        print(f"--- {ident.get('officialTitle')} ---")
        print(
            f"Last Update Posted: "
            f"{status.get('lastUpdatePostDateStruct', {}).get('date')}"
        )
        print(
            f"\nThe aim of the trial:\n"
            f"{protocol.get('descriptionModule', {}).get('briefSummary')}"
        )

        print(f"\nTrial Type: {design.get('studyType')}")
        print(f"Trial Phase: {', '.join(design.get('phases', [])) or 'N/A'}")
        print(f"Trial Status: {status.get('overallStatus')}")
        print(f"Minimum Age: {eligibility.get('minimumAge', 'N/A')}")
        print(f"Maximum Age: {eligibility.get('maximumAge', 'No Limit')}")

        contact = contacts.get("centralContacts", [{}])[0]
        contact_name = contact.get("name", "Contact Sponsor Directly")
        print(f"\nKey Contact: {contact_name}")

        print("\nHow the treatment works (Interventions):")
        for i in interventions:
            print(
                f"- {i.get('type')}: {i.get('name')} "
                f"({i.get('description', 'No description')})"
            )

        print(f"\nWho is the trial for?\n{inclusion}")
        print(f"\nWho is the trial not for?\n{exclusion}")

        print(f"\nURL: https://clinicaltrials.gov/study/{nct_id}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    get_trial_data("NCT07262970")
