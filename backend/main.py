from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

# Create the FastAPI app instance
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Sample data that mimics the required JSON structure
# This is our "mock" database for now.
mock_db_data = {
    "count": 2,
    "result": [
        {
            "NCTId": "NCT01234567",
            "BriefTitle": "A Study of a New Drug for Osteosarcoma",
            "CustomBriefSummary": "This is a patient-friendly summary of the first study.",
            "OverallStatus": "Recruiting",
            "Phase": "Phase 2",
            "LocationCountry": "United States",
            "LocationCity": "Houston"
        },
        {
            "NCTId": "NCT76543210",
            "BriefTitle": "Another Trial for Bone Cancer",
            "CustomBriefSummary": "This trial looks at the long-term effects of a treatment.",
            "OverallStatus": "Completed",
            "Phase": "Phase 3",
            "LocationCountry": "Canada, United Kingdom",
            "LocationCity": "Toronto, London"
        }
    ]
}

@app.get("/api/v1/trials")
def search_trials() -> Dict[str, Any]:
    """
    A mock endpoint to search for clinical trials.
    It ignores all query parameters and returns a hardcoded list of trials.
    """
    print("Request received. Returning mock data.")
    return mock_db_data

