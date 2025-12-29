import requests
import json

def get_trial_data(nct_id):
    # API v2 endpoint for a single study
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    
    # Selecting the specific fields needed for your template
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
        
        # Accessing nested data safely
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        contacts = protocol.get("contactsLocationsModule", {})
        interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])

        # Format Eligibility Criteria (Split Inclusion/Exclusion)
        criteria = eligibility.get("eligibilityCriteria", "")
        inclusion = "Not specified"
        exclusion = "Not specified"
        if "Inclusion Criteria:" in criteria and "Exclusion Criteria:" in criteria:
            parts = criteria.split("Exclusion Criteria:")
            inclusion = parts[0].replace("Inclusion Criteria:", "").strip()
            exclusion = parts[1].strip()

        # Build the Template Output
        print(f"--- {ident.get('officialTitle')} ---")
        print(f"Last Update Posted: {status.get('lastUpdatePostDateStruct', {}).get('date')}")
        print(f"\nThe aim of the trial:\n{protocol.get('descriptionModule', {}).get('briefSummary')}")
        
        print(f"\nTrial Type: {design.get('studyType')}")
        print(f"Trial Phase: {', '.join(design.get('phases', [])) or 'N/A'}")
        print(f"Trial Status: {status.get('overallStatus')}")
        print(f"Minimum Age: {eligibility.get('minimumAge', 'N/A')}")
        print(f"Maximum Age: {eligibility.get('maximumAge', 'No Limit')}")
        
        print(f"\nKey Contact: {contacts.get('centralContacts', [{}])[0].get('name', 'Contact Sponsor Directly')}")
        
        print("\nHow the treatment works (Interventions):")
        for i in interventions:
            print(f"- {i.get('type')}: {i.get('name')} ({i.get('description', 'No description')})")

        print(f"\nWho is the trial for?\n{inclusion}")
        print(f"\nWho is the trial not for?\n{exclusion}")
        
        print(f"\nURL: https://clinicaltrials.gov/study/{nct_id}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_trial_data("NCT07262970")