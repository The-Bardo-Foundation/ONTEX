"""
Daily ingestion pipeline — syncs clinical trials from ClinicalTrials.gov.

Run once every N hours (configured via settings.INGESTION_SCHEDULE_HOURS,
scheduled by APScheduler in main.py).

PIPELINE OVERVIEW
=================
Step 1  Collect NCT IDs + last-update dates for each search term
Step 2  Classify each NCT ID against the database (new / updated / rejected / no-change)
Step 3  Fetch full trial data from ClinicalTrials.gov API v2
Step 3.5 Capture existing custom_*/snapshot/approval state so re-ingestion
         preserves admin edits and enables Step 3.6 comparison
Step 3.6 Skip both UPDATED clinical_trials AND re-evaluated irrelevant_trials
         whose only changes are in settings.IGNORED_UPDATE_FIELDS (e.g. date,
         location, contact info). Affected rows have their official_* fields
         silently synced — no AI re-classification, no status reset.
Step 4  Classify relevance with AI (confident / unsure / reject)
Step 5  Generate patient-friendly custom_* fields via AI summarisation (confident/unsure only)
Step 6  Upsert into clinical_trials or irrelevant_trials
Step 7  Re-evaluate previously rejected trials whose data has changed
Step 8  Log run summary

TABLES
======
ClinicalTrial   — relevant trials (status: PENDING_REVIEW / APPROVED / REJECTED)
IrrelevantTrial — trials the AI marked irrelevant (kept for deduplication)

Both share ClinicalTrialBase fields (nct_id is primary key).

UPSERT BEHAVIOUR
================
SQLAlchemy's session.merge() is used for both inserts and updates.  When an
APPROVED trial is updated on ClinicalTrials.gov, the merge resets its status to
PENDING_REVIEW so reviewers can check what changed before it goes live again.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine, List, Optional

from sqlalchemy import select, update

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ClinicalTrial, IngestionEvent, IngestionRun, IrrelevantTrial, TrialStatus
from app.services.ai.classifier import classify_trial
from app.services.ai.client import AIClient
from app.services.ai.schemas import ClassificationResult, ConfidenceLabel
from app.services.ai.summarizer import ai_generate_summaries
from app.services.ctgov import iter_study_index_rows
from app.services.ctgov.study_detail import fetch_full_study, map_api_to_model
from app.services.ingestion_skip import is_content_unchanged

logger = logging.getLogger(__name__)


ProgressCallback = Optional[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]


async def run_daily_ingestion(
    search_terms: List[str] | None = None,
    progress_callback: ProgressCallback = None,
):
    if search_terms is None:
        search_terms = settings.SEARCH_TERMS

    async def emit(event: dict[str, Any]) -> None:
        if progress_callback:
            await progress_callback(event)

    # ──────────────────────────────────────────────────────────
    # STEP 1 — Collect NCT IDs + last-update dates for each term
    # ──────────────────────────────────────────────────────────
    # nct_id → last_update_posted_date (ISO 8601 string or "" if unknown)
    all_candidates: dict[str, str] = {}

    await emit({"step": "searching", "label": "Searching ClinicalTrials.gov"})

    for term in search_terms:
        # iter_study_index_rows is a blocking generator; run it in a thread
        # pool so it does not block the async event loop.
        rows = await asyncio.to_thread(
            lambda t=term: list(
                iter_study_index_rows(search_term=t, page_size=settings.PAGE_SIZE)
            )
        )
        for nct_id, last_update in rows:
            # Later search terms overwrite earlier ones for the same NCT ID;
            # the date is the same regardless of which term matched.
            all_candidates[nct_id] = last_update

    # ──────────────────────────────────────────────────────────
    # STEP 2 — Classify each NCT ID against our database
    # Three possible outcomes per candidate:
    #   new_trials     – NCT not in either table → fetch & process
    #   updated_trials – NCT in ClinicalTrial but date changed → re-fetch
    #   rejected_hits  – NCT in IrrelevantTrial → re-evaluate if date changed
    # ──────────────────────────────────────────────────────────
    new_trials: list[str] = []
    updated_trials: list[str] = []
    rejected_hits: list[tuple[str, str, str | None]] = []

    candidate_ids = list(all_candidates.keys())

    async with SessionLocal() as db:
        result = await db.execute(
            select(ClinicalTrial.nct_id, ClinicalTrial.last_update_post_date)
            .where(ClinicalTrial.nct_id.in_(candidate_ids))
        )
        existing_map = {row.nct_id: row.last_update_post_date for row in result}

        result = await db.execute(
            select(IrrelevantTrial.nct_id, IrrelevantTrial.last_update_post_date)
            .where(IrrelevantTrial.nct_id.in_(candidate_ids))
        )
        rejected_map = {row.nct_id: row.last_update_post_date for row in result}

    await emit({
        "step": "searching_done",
        "label": "Candidates found",
        "count": len(all_candidates),
    })

    for nct_id, api_date in all_candidates.items():
        if nct_id in existing_map:
            db_date = existing_map[nct_id] or ""
            if db_date != api_date:
                updated_trials.append(nct_id)
            continue

        if nct_id in rejected_map:
            rejected_hits.append((nct_id, api_date, rejected_map[nct_id]))
            continue

        new_trials.append(nct_id)

    # ──────────────────────────────────────────────────────────
    # STEP 7 prep — Determine which rejected trials need re-evaluation
    # (done here so reeval_list can extend trials_to_process before Step 3)
    # ──────────────────────────────────────────────────────────
    reeval_list = [
        nct_id
        for nct_id, api_date, stored_date in rejected_hits
        if api_date != (stored_date or "")
    ]

    # Precompute a set of nct_ids that came from rejected_hits for O(1) lookups
    # in the per-trial loop (avoids an O(n²) list rebuild per trial).
    rejected_nct_ids = {nct_id for nct_id, _, _ in rejected_hits}

    # ──────────────────────────────────────────────────────────
    # STEP 3 — Fetch full study data for all trials that need processing
    # ──────────────────────────────────────────────────────────
    trials_to_process = new_trials + updated_trials + reeval_list
    fetched: list[dict] = []
    fetch_errors = 0
    fetch_total = len(trials_to_process)

    await emit({
        "step": "fetching_details",
        "label": "Fetching trial details",
        "count": 0,
        "total": fetch_total,
    })

    for fetch_idx, nct_id in enumerate(trials_to_process):
        raw = await asyncio.to_thread(fetch_full_study, nct_id)
        if raw is None:
            logger.warning("Skipping %s — fetch_full_study returned None", nct_id)
            fetch_errors += 1
            continue
        mapped = map_api_to_model(raw)
        if not mapped.get("nct_id"):
            logger.warning("Skipping trial — map_api_to_model returned no nct_id for %s", nct_id)
            fetch_errors += 1
            continue
        fetched.append(mapped)
        await emit({
            "step": "fetching_details",
            "label": "Fetching trial details",
            "count": fetch_idx + 1,
            "total": fetch_total,
        })

    if not fetched:
        async with SessionLocal() as db:
            db.add(IngestionRun(
                run_at=datetime.utcnow(),
                search_terms=json.dumps(search_terms),
                candidates_found=len(all_candidates),
                new_trials=len(new_trials),
                updated_trials=len(updated_trials),
                reeval_trials=len(reeval_list),
                fetch_errors=fetch_errors,
            ))
            await db.commit()
        await emit({
            "step": "complete",
            "label": "Done — no trials to process",
            "new": 0,
            "updated": 0,
            "relevant": 0,
            "irrelevant": 0,
            "fetch_errors": fetch_errors,
            "classify_errors": 0,
        })
        logger.info(
            "Ingestion complete: no trials to process "
            "(search_terms=%s, candidates=%d, new=%d, updated=%d, reeval=%d, fetch_errors=%d)",
            search_terms, len(all_candidates), len(new_trials),
            len(updated_trials), len(reeval_list), fetch_errors,
        )
        return

    # ──────────────────────────────────────────────────────────
    # STEP 3.5 — Protect admin-edited custom_* fields on re-ingestion
    # For trials that already exist in the DB (updated or re-evaluated),
    # load their current non-null custom_* values so the AI summarisation
    # step does not overwrite content that an admin has manually edited.
    # ──────────────────────────────────────────────────────────
    _CUSTOM_FIELDS = [
        "custom_brief_title", "custom_brief_summary", "custom_overall_status",
        "custom_phase", "custom_study_type", "custom_location_country",
        "custom_location_city", "custom_minimum_age", "custom_maximum_age",
        "custom_central_contact_name", "custom_central_contact_phone",
        "custom_central_contact_email", "custom_eligibility_criteria",
        "custom_intervention_description", "custom_last_update_post_date",
        "key_information",
    ]

    # Only trials that were previously in the DB may have admin-edited fields.
    trials_with_existing_edits = set(updated_trials) | set(reeval_list)
    existing_custom_map: dict[str, dict] = {}  # nct_id → {field: non-null value}
    existing_approval_map: dict[str, dict] = {}  # nct_id → {approved_at, approved_by}
    existing_snapshot_map: dict[str, dict] = {}  # nct_id → snapshot of official_* fields

    _SNAPSHOT_FIELDS = [
        "brief_title", "brief_summary", "overall_status", "phase", "study_type",
        "location_country", "location_city", "minimum_age", "maximum_age",
        "central_contact_name", "central_contact_phone", "central_contact_email",
        "eligibility_criteria", "intervention_description", "last_update_post_date",
    ]

    if trials_with_existing_edits:
        fetched_existing_ids = {
            td["nct_id"] for td in fetched if td.get("nct_id") in trials_with_existing_edits
        }
        if fetched_existing_ids:
            async with SessionLocal() as db:
                for model_cls in (ClinicalTrial, IrrelevantTrial):
                    result = await db.execute(
                        select(model_cls).where(model_cls.nct_id.in_(fetched_existing_ids))
                    )
                    for row in result.scalars():
                        existing_custom_map[row.nct_id] = {
                            field: getattr(row, field)
                            for field in _CUSTOM_FIELDS
                            if getattr(row, field) is not None
                        }
                        # Snapshot every existing row (both tables) — Step 3.6
                        # compares this against the freshly-fetched payload.
                        existing_snapshot_map[row.nct_id] = {
                            field: getattr(row, field)
                            for field in _SNAPSHOT_FIELDS
                        }
                        if isinstance(row, ClinicalTrial) and row.approved_at:
                            existing_approval_map[row.nct_id] = {
                                "approved_at": row.approved_at,
                                "approved_by": row.approved_by,
                            }

    # ──────────────────────────────────────────────────────────
    # STEP 3.6 — Skip trials whose only changes are ignored fields
    # ClinicalTrials.gov frequently bumps last_update_post_date for
    # administrative touches (contact info, location adjustments) that have no
    # bearing on relevance or summary content. For both UPDATED clinical_trials
    # and re-evaluated irrelevant_trials, if every non-ignored field matches
    # the stored snapshot, silently sync official_* and skip AI rerun /
    # status reset.
    # ──────────────────────────────────────────────────────────
    updated_nct_id_set = set(updated_trials)
    unchanged_clinical: dict[str, dict] = {}
    unchanged_rejected: dict[str, dict] = {}

    for td in fetched:
        nct_id = td.get("nct_id")
        if not nct_id:
            continue
        snapshot = existing_snapshot_map.get(nct_id)
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

    def _build_sync_values(nct_id: str, td: dict) -> dict:
        """Construct the column→value dict for a Step 3.6 silent sync.

        Always overwrites every official_* column with the freshly-fetched
        value. For each ignored field that has a `custom_*` mirror column,
        the mirror is ALSO synced — but only when the admin hasn't manually
        edited it. "Not edited" = the stored custom value is None or still
        equals the previous official snapshot (i.e. it's a passthrough). This
        prevents stale `custom_location_*` / `custom_central_contact_*` /
        `custom_last_update_post_date` from being served by the public-facing
        WordPress template, which prefers `custom_*` when non-empty.
        """
        values = {f: td.get(f) for f in _SNAPSHOT_FIELDS}
        snapshot = existing_snapshot_map.get(nct_id, {})
        protected = existing_custom_map.get(nct_id, {})  # non-null customs only
        for field in settings.IGNORED_UPDATE_FIELDS:
            custom_field = f"custom_{field}"
            if custom_field not in _CUSTOM_FIELDS:
                continue
            existing_custom = protected.get(custom_field)  # None if was null
            existing_official = snapshot.get(field)
            if existing_custom is None or existing_custom == existing_official:
                values[custom_field] = td.get(field)
        return values

    if unchanged_clinical or unchanged_rejected:
        skipped_ids = set(unchanged_clinical) | set(unchanged_rejected)
        fetched = [td for td in fetched if td.get("nct_id") not in skipped_ids]

        async with SessionLocal() as db:
            for nct_id, td in unchanged_clinical.items():
                await db.execute(
                    update(ClinicalTrial)
                    .where(ClinicalTrial.nct_id == nct_id)
                    .values(**_build_sync_values(nct_id, td))
                )
            for nct_id, td in unchanged_rejected.items():
                await db.execute(
                    update(IrrelevantTrial)
                    .where(IrrelevantTrial.nct_id == nct_id)
                    .values(**_build_sync_values(nct_id, td))
                )
            await db.commit()

        await emit({
            "step": "unchanged_skipped",
            "label": "Skipped (content unchanged)",
            "count": clinical_skipped + rejected_skipped,
        })

    # ──────────────────────────────────────────────────────────
    # STEP 4 — Relevance classification
    # AIClient is instantiated once per run (one connection pool).
    # If OPENROUTER_API_KEY is not set, AIClient raises RuntimeError here.
    # ──────────────────────────────────────────────────────────
    ai_client = AIClient()
    classify_errors = 0
    classify_total = len(fetched)

    # classifications[nct_id] = ClassificationResult
    classifications: dict[str, ClassificationResult] = {}

    await emit({
        "step": "classifying",
        "label": "AI classification",
        "count": 0,
        "total": classify_total,
    })

    for classify_idx, trial_data in enumerate(fetched):
        nct_id = trial_data.get("nct_id")
        try:
            classification = await classify_trial(ai_client, trial_data)
        except Exception as exc:
            logger.error("classify_trial raised for %s: %s", nct_id, exc)
            classify_errors += 1
            # Fail-safe: include for manual review rather than silently skip
            classification = ClassificationResult(
                label=ConfidenceLabel.UNSURE,
                reason=f"Classification error — needs manual review: {exc}",
            )
        classifications[nct_id] = classification
        await emit({
            "step": "classifying",
            "label": "AI classification",
            "count": classify_idx + 1,
            "total": classify_total,
        })

    # Split fetched trials: only confident/unsure get AI summaries
    to_summarize = [
        td for td in fetched
        if classifications.get(td.get("nct_id"), ClassificationResult(
            label=ConfidenceLabel.REJECT, reason=""
        )).label != ConfidenceLabel.REJECT
    ]
    to_reject = [
        td for td in fetched
        if td not in to_summarize
    ]

    # ──────────────────────────────────────────────────────────
    # STEP 5 — AI summarisation: populate custom_* fields for relevant trials only
    # ──────────────────────────────────────────────────────────
    summarize_total = len(to_summarize)

    await emit({
        "step": "summarizing",
        "label": "Generating summaries",
        "count": 0,
        "total": summarize_total,
    })

    for summarize_idx, trial_data in enumerate(to_summarize):
        custom_fields = await ai_generate_summaries(ai_client, trial_data)
        # Apply AI-generated fields, but preserve any non-null admin-edited values.
        protected = existing_custom_map.get(trial_data.get("nct_id"), {})
        for field, value in custom_fields.items():
            trial_data[field] = protected.get(field, value)
        await emit({
            "step": "summarizing",
            "label": "Generating summaries",
            "count": summarize_idx + 1,
            "total": summarize_total,
        })

    # ──────────────────────────────────────────────────────────
    # STEP 6 — Database upsert
    # ──────────────────────────────────────────────────────────
    processed = 0
    newly_irrelevant = 0

    # Used to set ingestion_event: updated_trials are UPDATED, everything else is NEW
    # content_unchanged trials were already handled in Step 3.6 and removed from fetched.
    updated_nct_ids = updated_nct_id_set

    async with SessionLocal() as db:
        for trial_data in to_summarize:
            nct_id = trial_data.get("nct_id")
            classification = classifications[nct_id]
            approval_history = existing_approval_map.get(nct_id, {})
            event = IngestionEvent.UPDATED if nct_id in updated_nct_ids else IngestionEvent.NEW
            snapshot = existing_snapshot_map.get(nct_id)
            trial = ClinicalTrial(
                **trial_data,
                status=TrialStatus.PENDING_REVIEW,
                ingestion_event=event,
                ai_relevance_label=classification.label.value,
                ai_relevance_reason=classification.reason,
                previous_approved_at=approval_history.get("approved_at"),
                previous_approved_by=approval_history.get("approved_by"),
                previous_official_snapshot=json.dumps(snapshot) if snapshot else None,
            )
            await db.merge(trial)

            if nct_id in rejected_nct_ids:
                existing_irrelevant = await db.get(IrrelevantTrial, nct_id)
                if existing_irrelevant:
                    await db.delete(existing_irrelevant)

            processed += 1

        for trial_data in to_reject:
            nct_id = trial_data.get("nct_id")
            classification = classifications[nct_id]
            event = IngestionEvent.UPDATED if nct_id in updated_nct_ids else IngestionEvent.NEW
            irrelevant = IrrelevantTrial(
                **trial_data,
                ai_relevance_label=classification.label.value,
                ai_relevance_reason=classification.reason,
                rejected_at=datetime.utcnow(),
                rejected_by=None,
                ingestion_event=event,
            )
            await db.merge(irrelevant)

            existing_clinical = await db.get(ClinicalTrial, nct_id)
            if existing_clinical:
                await db.delete(existing_clinical)
            newly_irrelevant += 1

        await db.commit()

    # ──────────────────────────────────────────────────────────
    # STEP 8 — Write ingestion run record + log summary
    # ──────────────────────────────────────────────────────────
    updated_trials_count = len(updated_trials) - clinical_skipped
    reeval_trials_count = len(reeval_list) - rejected_skipped
    skipped_unchanged_count = clinical_skipped + rejected_skipped

    async with SessionLocal() as db:
        db.add(IngestionRun(
            run_at=datetime.utcnow(),
            search_terms=json.dumps(search_terms),
            candidates_found=len(all_candidates),
            new_trials=len(new_trials),
            updated_trials=updated_trials_count,
            reeval_trials=reeval_trials_count,
            relevant_processed=processed,
            irrelevant_processed=newly_irrelevant,
            fetch_errors=fetch_errors,
            classify_errors=classify_errors,
            skipped_unchanged=skipped_unchanged_count,
        ))
        await db.commit()

    await emit({
        "step": "complete",
        "label": "Done",
        "new": len(new_trials),
        "updated": updated_trials_count,
        "skipped_unchanged": skipped_unchanged_count,
        "relevant": processed,
        "irrelevant": newly_irrelevant,
        "fetch_errors": fetch_errors,
        "classify_errors": classify_errors,
    })

    logger.info(
        "Ingestion complete: %d new, %d updated, %d skipped (unchanged), %d re-evaluated | "
        "%d relevant (PENDING_REVIEW), %d irrelevant | "
        "%d fetch errors, %d classify errors | "
        "search_terms=%s, total_candidates=%d",
        len(new_trials),
        updated_trials_count,
        skipped_unchanged_count,
        reeval_trials_count,
        processed,
        newly_irrelevant,
        fetch_errors,
        classify_errors,
        search_terms,
        len(all_candidates),
    )


if __name__ == "__main__":
    asyncio.run(run_daily_ingestion())
