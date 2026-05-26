"""
Helper for ingestion Step 3.6 — decide when an updated/re-evaluated trial can
skip AI re-classification and re-summarisation.

The ingestion pipeline detects "an update" purely by comparing
`last_update_post_date` between ClinicalTrials.gov and our database. But
ClinicalTrials.gov frequently bumps that date for purely administrative reasons
(contact-info edits, location additions/removals, etc.) that have no bearing on
whether the trial is relevant to osteosarcoma or what the patient-facing
summary should say.

`is_content_unchanged()` decides whether the new payload is "content-equivalent"
to the stored snapshot — i.e. every field that *isn't* in the ignored list is
identical. Caller passes the ignored list in (typically
`settings.IGNORED_UPDATE_FIELDS`), keeping this helper pure and unit-testable.
"""

from typing import Iterable, Mapping


def is_content_unchanged(
    new: Mapping[str, object],
    old: Mapping[str, object],
    ignored: Iterable[str],
) -> bool:
    """Return True if `new` matches `old` on every field except those in `ignored`.

    Only fields present in `old` (the stored snapshot) are compared. Fields in
    `new` that have no counterpart in `old` are not considered — the snapshot
    defines the comparison universe.

    Args:
        new:      Freshly-fetched trial data (e.g. output of map_api_to_model).
        old:      Snapshot of the same trial as currently stored in the DB.
        ignored:  Field names whose changes should be ignored.

    Returns:
        True  → no meaningful content change; caller can silently sync the DB
                row and skip AI re-classification/re-summarisation.
        False → at least one non-ignored field differs; caller must run the
                normal re-evaluation pipeline.
    """
    ignored_set = set(ignored)
    for field in old.keys():
        if field in ignored_set:
            continue
        if new.get(field) != old.get(field):
            return False
    return True
