"""Unit tests for app.services.ingestion_skip.is_content_unchanged."""

from app.services.ingestion_skip import is_content_unchanged


IGNORED = ["last_update_post_date", "location_city"]


def test_identical_payloads_unchanged():
    old = {"brief_title": "T", "phase": "Phase 2", "last_update_post_date": "2024-01-01"}
    assert is_content_unchanged(old, old, IGNORED) is True


def test_only_ignored_field_changes_unchanged():
    old = {"brief_title": "T", "phase": "Phase 2", "last_update_post_date": "2024-01-01"}
    new = {"brief_title": "T", "phase": "Phase 2", "last_update_post_date": "2024-09-01"}
    assert is_content_unchanged(new, old, IGNORED) is True


def test_multiple_ignored_fields_change_unchanged():
    old = {
        "brief_title": "T", "phase": "Phase 2",
        "last_update_post_date": "2024-01-01", "location_city": "Oslo",
    }
    new = {
        "brief_title": "T", "phase": "Phase 2",
        "last_update_post_date": "2024-09-01", "location_city": "Bergen",
    }
    assert is_content_unchanged(new, old, IGNORED) is True


def test_non_ignored_field_change_detected():
    old = {"brief_title": "Old Title", "phase": "Phase 2", "last_update_post_date": "2024-01-01"}
    new = {"brief_title": "New Title", "phase": "Phase 2", "last_update_post_date": "2024-09-01"}
    assert is_content_unchanged(new, old, IGNORED) is False


def test_missing_field_in_new_treated_as_change():
    old = {"brief_title": "T", "phase": "Phase 2", "last_update_post_date": "2024-01-01"}
    new = {"brief_title": "T", "last_update_post_date": "2024-01-01"}  # phase missing
    assert is_content_unchanged(new, old, IGNORED) is False


def test_extra_field_in_new_ignored():
    """Snapshot defines comparison universe; extra fields in `new` don't trigger change."""
    old = {"brief_title": "T", "last_update_post_date": "2024-01-01"}
    new = {"brief_title": "T", "last_update_post_date": "2024-01-01", "extra": "x"}
    assert is_content_unchanged(new, old, IGNORED) is True


def test_empty_ignored_list():
    old = {"brief_title": "T", "last_update_post_date": "2024-01-01"}
    new = {"brief_title": "T", "last_update_post_date": "2024-09-01"}
    assert is_content_unchanged(new, old, ignored=[]) is False
