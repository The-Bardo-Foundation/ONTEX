"""
Fetches and prints clinical trial data from the ClinicalTrials.gov API v2.

Used as a diagnostic/debug helper during ingestion development.
For bulk index fetching see study_index.iter_study_index_rows.
"""

import requests


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
