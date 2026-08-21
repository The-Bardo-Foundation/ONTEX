"""
Helpers for ingestion Steps 3.5 & 3.6 — preserving admin edits on re-ingestion
and deciding when an updated/re-evaluated trial can skip AI re-classification
and re-summarisation.

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

`load_existing_trial_state()` (Step 3.5) and `skip_unchanged_trials()`
(Step 3.6) own the DB I/O for these phases. The caller passes in its own
`session_factory` (e.g. the ingestion module's `SessionLocal`) so test
monkeypatching of that factory keeps working and these helpers stay decoupled
from the orchestration module.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Mapping

from sqlalchemy import select, update

from app.core.config import settings
from app.db.models import ClinicalTrial, IrrelevantTrial

EmitFn = Callable[[dict[str, Any]], Awaitable[None]]

CUSTOM_FIELDS = [
    "custom_brief_title", "custom_brief_summary", "custom_overall_status",
    "custom_phase", "custom_study_type", "custom_location_country",
    "custom_location_city", "custom_minimum_age", "custom_maximum_age",
    "custom_central_contact_name", "custom_central_contact_phone",
    "custom_central_contact_email", "custom_eligibility_criteria",
    "custom_intervention_description", "custom_last_update_post_date",
    "key_information",
]

SNAPSHOT_FIELDS = [
    "brief_title", "brief_summary", "overall_status", "phase", "study_type",
    "location_country", "location_city", "minimum_age", "maximum_age",
    "central_contact_name", "central_contact_phone", "central_contact_email",
    "eligibility_criteria", "intervention_description", "last_update_post_date",
]


@dataclass
class ExistingTrialState:
    """Step 3.5 output: preserved admin edits and pre-update snapshots."""

    custom_map: dict[str, dict] = field(default_factory=dict)
    approval_map: dict[str, dict] = field(default_factory=dict)
    snapshot_map: dict[str, dict] = field(default_factory=dict)


@dataclass
class UnchangedSkipResult:
    """Step 3.6 output: trials silently synced without AI re-processing."""

    clinical_skipped: int = 0
    rejected_skipped: int = 0
    remaining_fetched: list[dict] = field(default_factory=list)


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
    for field_name in old.keys():
        if field_name in ignored_set:
            continue
        if new.get(field_name) != old.get(field_name):
            return False
    return True


async def load_existing_trial_state(
    session_factory: Callable[[], Any],
    trials_with_existing_edits: set[str],
    fetched: list[dict],
) -> ExistingTrialState:
    """Step 3.5 — Protect admin-edited custom_* fields on re-ingestion.

    For trials that already exist in the DB (updated or re-evaluated), load
    their current non-null custom_* values so the AI summarisation step does
    not overwrite content an admin has manually edited, plus a snapshot of the
    official_* fields (for Step 3.6 comparison) and any approval history.
    """
    state = ExistingTrialState()

    if not trials_with_existing_edits:
        return state

    fetched_existing_ids = {
        td["nct_id"] for td in fetched if td.get("nct_id") in trials_with_existing_edits
    }
    if not fetched_existing_ids:
        return state

    async with session_factory() as db:
        for model_cls in (ClinicalTrial, IrrelevantTrial):
            result = await db.execute(
                select(model_cls).where(model_cls.nct_id.in_(fetched_existing_ids))
            )
            for row in result.scalars():
                state.custom_map[row.nct_id] = {
                    field_name: getattr(row, field_name)
                    for field_name in CUSTOM_FIELDS
                    if getattr(row, field_name) is not None
                }
                state.snapshot_map[row.nct_id] = {
                    field_name: getattr(row, field_name)
                    for field_name in SNAPSHOT_FIELDS
                }
                if isinstance(row, ClinicalTrial) and row.approved_at:
                    state.approval_map[row.nct_id] = {
                        "approved_at": row.approved_at,
                        "approved_by": row.approved_by,
                    }

    return state


def build_sync_values(
    nct_id: str,
    td: dict,
    existing_snapshot_map: dict[str, dict],
    existing_custom_map: dict[str, dict],
) -> dict:
    """Construct the column→value dict for a Step 3.6 silent sync.

    Always overwrites every official_* column with the freshly-fetched value.
    For each ignored field that has a `custom_*` mirror column, the mirror is
    ALSO synced — but only when the admin hasn't manually edited it. "Not
    edited" = the stored custom value is None or still equals the previous
    official snapshot (i.e. it's a passthrough). This prevents stale `custom_*`
    fields from being served.
    """
    values = {f: td.get(f) for f in SNAPSHOT_FIELDS}
    snapshot = existing_snapshot_map.get(nct_id, {})
    protected = existing_custom_map.get(nct_id, {})
    for field_name in settings.IGNORED_UPDATE_FIELDS:
        custom_field = f"custom_{field_name}"
        if custom_field not in CUSTOM_FIELDS:
            continue
        existing_custom = protected.get(custom_field)
        existing_official = snapshot.get(field_name)
        if existing_custom is None or existing_custom == existing_official:
            values[custom_field] = td.get(field_name)
    return values


async def skip_unchanged_trials(
    session_factory: Callable[[], Any],
    fetched: list[dict],
    *,
    updated_trials: list[str],
    rejected_nct_ids: set[str],
    existing_state: ExistingTrialState,
    emit: EmitFn,
) -> UnchangedSkipResult:
    """Step 3.6 — Skip trials whose only changes are ignored fields.

    For both UPDATED clinical_trials and re-evaluated irrelevant_trials, if
    every non-ignored field matches the stored snapshot, silently sync
    official_* (and passthrough custom_*) and drop the trial from `fetched` so
    it skips AI rerun / status reset.
    """
    updated_nct_id_set = set(updated_trials)
    unchanged_clinical: dict[str, dict] = {}
    unchanged_rejected: dict[str, dict] = {}

    for td in fetched:
        nct_id = td.get("nct_id")
        if not nct_id:
            continue
        snapshot = existing_state.snapshot_map.get(nct_id)
        if not snapshot:
            continue
        if not is_content_unchanged(td, snapshot, settings.IGNORED_UPDATE_FIELDS):
            continue
        if nct_id in updated_nct_id_set:
            unchanged_clinical[nct_id] = td
        elif nct_id in rejected_nct_ids:
            unchanged_rejected[nct_id] = td

    clinical_skipped = len(unchanged_clinical)
    rejected_skipped = len(unchanged_rejected)

    if unchanged_clinical or unchanged_rejected:
        skipped_ids = set(unchanged_clinical) | set(unchanged_rejected)
        fetched = [td for td in fetched if td.get("nct_id") not in skipped_ids]

        async with session_factory() as db:
            for nct_id, td in unchanged_clinical.items():
                await db.execute(
                    update(ClinicalTrial)
                    .where(ClinicalTrial.nct_id == nct_id)
                    .values(**build_sync_values(
                        nct_id, td,
                        existing_state.snapshot_map,
                        existing_state.custom_map,
                    ))
                )
            for nct_id, td in unchanged_rejected.items():
                await db.execute(
                    update(IrrelevantTrial)
                    .where(IrrelevantTrial.nct_id == nct_id)
                    .values(**build_sync_values(
                        nct_id, td,
                        existing_state.snapshot_map,
                        existing_state.custom_map,
                    ))
                )
            await db.commit()

        await emit({
            "step": "unchanged_skipped",
            "label": "Skipped (content unchanged)",
            "count": clinical_skipped + rejected_skipped,
        })

    return UnchangedSkipResult(
        clinical_skipped=clinical_skipped,
        rejected_skipped=rejected_skipped,
        remaining_fetched=fetched,
    )
