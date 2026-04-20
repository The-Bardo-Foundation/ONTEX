"""
Daily ingestion pipeline — syncs clinical trials from ClinicalTrials.gov.

Run once every N hours (configured via settings.INGESTION_SCHEDULE_HOURS,
scheduled by APScheduler in main.py).

PIPELINE OVERVIEW
=================
Step 1  Collect NCT IDs + last-update dates for each search term
Step 2  Classify each NCT ID against the database (new / updated / rejected / no-change)
Step 3  Fetch full trial data from ClinicalTrials.gov API v2
Step 3.6 Skip UPDATED trials whose content hasn't changed (date-only bumps)
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
    # Content fields exclude last_update_post_date: a date change is what triggered
    # the UPDATED path, so we compare everything *except* the date to decide whether
    # actual content changed and a re-review is needed.
    _CONTENT_FIELDS = [f for f in _SNAPSHOT_FIELDS if f != "last_update_post_date"]

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
                        # Capture approval metadata and snapshot for ClinicalTrial rows
                        if isinstance(row, ClinicalTrial):
                            # Snapshot ALL existing trials for content-change comparison
                            # (Step 3.6), not just approved ones.
                            existing_snapshot_map[row.nct_id] = {
                                field: getattr(row, field)
                                for field in _SNAPSHOT_FIELDS
                            }
                            if row.approved_at:
                                existing_approval_map[row.nct_id] = {
                                    "approved_at": row.approved_at,
                                    "approved_by": row.approved_by,
                                }

    # ──────────────────────────────────────────────────────────
    # STEP 3.6 — Skip UPDATED trials whose content hasn't changed
    # ClinicalTrials.gov sometimes bumps last_update_post_date without changing
    # any actual content (administrative touches). For those trials, skip
    # re-classification, re-summarisation, and status reset — just silently
    # update the date columns so future runs don't flag them again.
    # ──────────────────────────────────────────────────────────
    updated_nct_id_set = set(updated_trials)
    content_unchanged: list[str] = []

    # Collect date + trial_data for candidates before mutating fetched
    unchanged_candidates: dict[str, dict] = {
        td["nct_id"]: td
        for td in fetched
        if td.get("nct_id") in updated_nct_id_set
        and td.get("nct_id") in existing_snapshot_map
        and all(
            td.get(f) == existing_snapshot_map[td["nct_id"]].get(f)
            for f in _CONTENT_FIELDS
        )
    }

    if unchanged_candidates:
        content_unchanged = list(unchanged_candidates.keys())
        fetched = [td for td in fetched if td.get("nct_id") not in unchanged_candidates]

        async with SessionLocal() as db:
            for nct_id, td in unchanged_candidates.items():
                new_date = td.get("last_update_post_date")
                await db.execute(
                    update(ClinicalTrial)
                    .where(ClinicalTrial.nct_id == nct_id)
                    .values(
                        last_update_post_date=new_date,
                        custom_last_update_post_date=new_date,
                    )
                )
            await db.commit()

        await emit({
            "step": "unchanged_skipped",
            "label": "Skipped (content unchanged)",
            "count": len(content_unchanged),
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
            irrelevant = IrrelevantTrial(
                **trial_data,
                irrelevance_reason=classification.reason,
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
    async with SessionLocal() as db:
        db.add(IngestionRun(
            run_at=datetime.utcnow(),
            search_terms=json.dumps(search_terms),
            candidates_found=len(all_candidates),
            new_trials=len(new_trials),
            updated_trials=len(updated_trials) - len(content_unchanged),
            reeval_trials=len(reeval_list),
            relevant_processed=processed,
            irrelevant_processed=newly_irrelevant,
            fetch_errors=fetch_errors,
            classify_errors=classify_errors,
            skipped_unchanged=len(content_unchanged),
        ))
        await db.commit()

    await emit({
        "step": "complete",
        "label": "Done",
        "new": len(new_trials),
        "updated": len(updated_trials) - len(content_unchanged),
        "skipped_unchanged": len(content_unchanged),
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
        len(updated_trials) - len(content_unchanged),
        len(content_unchanged),
        len(reeval_list),
        processed,
        newly_irrelevant,
        fetch_errors,
        classify_errors,
        search_terms,
        len(all_candidates),
    )


if __name__ == "__main__":
    asyncio.run(run_daily_ingestion())
