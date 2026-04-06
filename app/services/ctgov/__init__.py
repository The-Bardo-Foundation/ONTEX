"""
Public API for the ClinicalTrials.gov service layer.

Re-exports the two primary helpers used throughout the ingestion pipeline:
  - iter_study_index_rows: paginated index fetch (NCT ID + last-update date)
  - get_trial_data:        single-study detail fetch and formatted print
"""

from app.services.ctgov.study_detail import get_trial_data
from app.services.ctgov.study_index import iter_study_index_rows

__all__ = ["iter_study_index_rows", "get_trial_data"]
