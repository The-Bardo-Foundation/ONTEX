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
         silently synced - no AI re-classification, no status reset.
Step 4  Classify relevance with AI (confident / unsure / reject). If the AI call
        itself fails (outage/error), the trial is skipped entirely this run — no row
        is written — so Step 2's date-diff logic refetches and re-evaluates it next run.
Step 5  Generate patient-friendly custom_* fields via AI summarisation (confident/unsure only)
Step 6  Upsert into clinical_trials or irrelevant_trials; promote previously-
        rejected NCTs to clinical_trials (and delete their IrrelevantTrial row)
        when AI now classifies them as relevant - and vice versa
Step 7  Log run summary

TABLES
======
ClinicalTrial   - relevant trials (status: PENDING_REVIEW / APPROVED / REJECTED)
IrrelevantTrial - trials the AI marked irrelevant (kept for deduplication)

Both share ClinicalTrialBase fields (nct_id is primary key).

UPSERT BEHAVIOUR
================
SQLAlchemy's session.merge() is used for both inserts and updates.

Status assignment in Step 6:
  - AI label "confident" → APPROVED, approved_by="ai" (auto-published, no human review)
  - AI label "unsure"    → PENDING_REVIEW (queued for editorial review)
  - AI label "reject"    → IrrelevantTrial table (not in ClinicalTrial at all)
  - AI call failed       → skipped entirely (no row written); refetched next run

Previously human-approved trials that are re-ingested as confident preserve the original
human approver in approved_by/approved_at — AI re-confirmation does not overwrite human
authorship. Updated trials that drop to "unsure" revert to PENDING_REVIEW.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, List, Optional

from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ClinicalTrial, IngestionEvent, IngestionRun, IrrelevantTrial, TrialStatus
from app.services.ai.classifier import classify_trial
from app.services.ai.client import AIClient
from app.services.ai.schemas import ClassificationResult, ConfidenceLabel
from app.services.ai.summarizer import ai_generate_summaries
from app.services.ctgov import iter_study_index_rows
from app.services.ctgov.study_detail import fetch_full_study, map_api_to_model
from app.services.ingestion_skip import (
    UnchangedSkipResult,
    load_existing_trial_state,
    skip_unchanged_trials,
)
from app.services.ingestion_utils.email import send_ingestion_summary

logger = logging.getLogger(__name__)

# Stored in ClinicalTrial.approved_by to distinguish AI vs. human approvals.
AI_APPROVER = "ai"

ProgressCallback = Optional[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]
EmitFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class CandidateBuckets:
    """Step 2 output: how each CT.gov candidate maps to our database."""

    new_trials: list[str] = field(default_factory=list)
    updated_trials: list[str] = field(default_factory=list)
    reeval_list: list[str] = field(default_factory=list)
    rejected_nct_ids: set[str] = field(default_factory=set)


def _make_emit(progress_callback: ProgressCallback) -> EmitFn:
    async def emit(event: dict[str, Any]) -> None:
        if progress_callback:
            await progress_callback(event)
    return emit


async def _collect_candidates(search_terms: list[str], emit: EmitFn) -> dict[str, str]:
    """Step 1 — Collect NCT IDs + last-update dates for each search term."""
    all_candidates: dict[str, str] = {}

    await emit({"step": "searching", "label": "Searching ClinicalTrials.gov"})

    for term in search_terms:
        rows = await asyncio.to_thread(
            lambda t=term: list(
                iter_study_index_rows(search_term=t, page_size=settings.PAGE_SIZE)
            )
        )
        for nct_id, last_update in rows:
            # Later search terms overwrite earlier ones for the same NCT ID;
            # the date is the same regardless of which term matched.
            all_candidates[nct_id] = last_update

    return all_candidates


async def _classify_candidates(
    all_candidates: dict[str, str],
    emit: EmitFn,
) -> CandidateBuckets:
    """Step 2 — Classify each NCT ID against our database.

    Three possible outcomes per candidate:
      new_trials     – NCT not in either table → fetch & process
      updated_trials – NCT in ClinicalTrial but date changed → re-fetch
      rejected_hits  – NCT in IrrelevantTrial → re-evaluate if date changed
    """
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

    # Filter rejected candidates by date diff: only those whose CT.gov
    # last_update_post_date has advanced since we last stored them are worth
    # re-fetching. Their fetch + classify happens in the shared Steps 3-6 path
    # (no dedicated reeval block).
    reeval_list = [
        nct_id
        for nct_id, api_date, stored_date in rejected_hits
        if api_date != (stored_date or "")
    ]

    return CandidateBuckets(
        new_trials=new_trials,
        updated_trials=updated_trials,
        reeval_list=reeval_list,
        # Precomputed as a set for O(1) lookups in the per-trial loops of
        # Steps 3.6 and 6 (avoids an O(n^2) list rebuild per trial).
        rejected_nct_ids={nct_id for nct_id, _, _ in rejected_hits},
    )


async def _fetch_trial_details(
    trials_to_process: list[str],
    emit: EmitFn,
) -> tuple[list[dict], int]:
    """Step 3 — Fetch full study data for all trials that need processing."""
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

    return fetched, fetch_errors


async def _record_empty_run(
    *,
    search_terms: list[str],
    all_candidates: dict[str, str],
    buckets: CandidateBuckets,
    fetch_errors: int,
    emit: EmitFn,
) -> None:
    """Early exit — Step 3 fetched nothing, so log the run and skip Steps 3.5-7.

    The audit row still records what Step 2 found, so a run where every fetch
    errored is distinguishable from a run with no candidates at all.
    """
    async with SessionLocal() as db:
        db.add(IngestionRun(
            run_at=datetime.utcnow(),
            search_terms=json.dumps(search_terms),
            candidates_found=len(all_candidates),
            new_trials=len(buckets.new_trials),
            updated_trials=len(buckets.updated_trials),
            reeval_trials=len(buckets.reeval_list),
            fetch_errors=fetch_errors,
        ))
        await db.commit()

    # Same key set as _record_ingestion_run's final_summary so both terminal
    # paths produce an identical email table. The new/updated/reevaluated counts
    # here are candidates identified, not work completed — this branch is also
    # reached when every fetch failed, which `fetch_errors` and the label make
    # visible.
    empty_summary = {
        "step": "complete",
        "label": "Done — no trials to process",
        "search_terms": search_terms,
        "candidates_found": len(all_candidates),
        "new": len(buckets.new_trials),
        "updated": len(buckets.updated_trials),
        "skipped_unchanged": 0,
        "reevaluated": len(buckets.reeval_list),
        "relevant": 0,
        "auto_approved": 0,
        "pending_review": 0,
        "irrelevant": 0,
        "fetch_errors": fetch_errors,
        "classify_errors": 0,
    }
    await emit(empty_summary)
    logger.info(
        "Ingestion complete: no trials to process "
        "(search_terms=%s, candidates=%d, new=%d, updated=%d, reeval=%d, fetch_errors=%d)",
        search_terms, len(all_candidates), len(buckets.new_trials),
        len(buckets.updated_trials), len(buckets.reeval_list), fetch_errors,
    )
    await send_ingestion_summary(empty_summary)


# ──────────────────────────────────────────────────────────
# STEP 4 — Relevance classification
# Three verdicts plus a failure mode:
#   confident / unsure – trial is relevant enough to summarise (Step 5)
#   reject             – no osteosarcoma connection → irrelevant_trials
#   failed             – the AI call itself errored → trial stored NOWHERE
# ──────────────────────────────────────────────────────────
async def _classify_fetched_trials(
    fetched: list[dict],
    ai_client: AIClient,
    emit: EmitFn,
) -> tuple[dict[str, ClassificationResult], set[str]]:
    """Step 4 — Relevance classification.

    Returns (classifications, failed_ids). Trials in `failed_ids` are ones whose
    classification genuinely failed (LLM outage/error); they are written NOWHERE
    this run — leaving the DB untouched so Step 2's date-diff logic refetches and
    re-evaluates them on the next daily run.
    """
    # classifications[nct_id] = ClassificationResult
    classifications: dict[str, ClassificationResult] = {}
    classify_total = len(fetched)

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
            # Genuine AI failure: flag it so this trial is skipped (not stored) and
            # refetched on the next run, rather than parked as a bogus "unsure".
            classification = ClassificationResult(
                label=ConfidenceLabel.UNSURE,
                # Truncated: reason has max_length=500, and a ValidationError
                # raised here would abort the whole run.
                reason=f"Classification error: {exc}"[:500],
                failed=True,
            )
        classifications[nct_id] = classification
        await emit({
            "step": "classifying",
            "label": "AI classification",
            "count": classify_idx + 1,
            "total": classify_total,
        })

    failed_ids = {nct for nct, c in classifications.items() if c.failed}
    return classifications, failed_ids


def _split_by_relevance(
    fetched: list[dict],
    classifications: dict[str, ClassificationResult],
    failed_ids: set[str],
) -> tuple[list[dict], list[dict]]:
    """Split fetched trials on their Step 4 verdict.

    Only confident/unsure (and not failed) get AI summaries; reject (and not
    failed) go to the irrelevant table; failed go nowhere.
    """
    to_summarize = [
        td for td in fetched
        if td.get("nct_id") not in failed_ids
        and classifications[td.get("nct_id")].label != ConfidenceLabel.REJECT
    ]
    to_reject = [
        td for td in fetched
        if td.get("nct_id") not in failed_ids
        and classifications[td.get("nct_id")].label == ConfidenceLabel.REJECT
    ]
    return to_summarize, to_reject


async def _summarize_trials(
    to_summarize: list[dict],
    ai_client: AIClient,
    existing_custom_map: dict[str, dict],
    emit: EmitFn,
) -> None:
    """Step 5 — AI summarisation for relevant trials."""
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
        for field_name, value in custom_fields.items():
            trial_data[field_name] = protected.get(field_name, value)
        await emit({
            "step": "summarizing",
            "label": "Generating summaries",
            "count": summarize_idx + 1,
            "total": summarize_total,
        })


async def _upsert_trials(
    to_summarize: list[dict],
    to_reject: list[dict],
    *,
    classifications: dict[str, ClassificationResult],
    updated_nct_ids: set[str],
    rejected_nct_ids: set[str],
    existing_approval_map: dict[str, dict],
    existing_snapshot_map: dict[str, dict],
) -> tuple[int, int, int, int]:
    """Step 6 — Database upsert.

    Returns (processed, auto_approved, pending_review, newly_irrelevant).
    """
    processed = 0
    auto_approved = 0
    pending_review = 0
    newly_irrelevant = 0

    async with SessionLocal() as db:
        now = datetime.utcnow()
        for trial_data in to_summarize:
            nct_id = trial_data.get("nct_id")
            classification = classifications[nct_id]
            approval_history = existing_approval_map.get(nct_id, {})
            event = IngestionEvent.UPDATED if nct_id in updated_nct_ids else IngestionEvent.NEW
            snapshot = existing_snapshot_map.get(nct_id)

            # All confident classifications auto-approve — no human check needed.
            # Previously human-approved trials preserve the original approver so
            # AI re-ingestion does not overwrite human authorship in the audit trail.
            if classification.label == ConfidenceLabel.CONFIDENT:
                status = TrialStatus.APPROVED
                prior_by = approval_history.get("approved_by")
                approved_by = prior_by if (prior_by and prior_by != AI_APPROVER) else AI_APPROVER
                approved_at = approval_history.get("approved_at") if approved_by != AI_APPROVER else now
                auto_approved += 1
            else:
                status = TrialStatus.PENDING_REVIEW
                approved_at = None
                approved_by = None
                pending_review += 1

            trial = ClinicalTrial(
                **trial_data,
                status=status,
                approved_at=approved_at,
                approved_by=approved_by,
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

    return processed, auto_approved, pending_review, newly_irrelevant


async def _record_ingestion_run(
    *,
    search_terms: list[str],
    all_candidates: dict[str, str],
    buckets: CandidateBuckets,
    skip_result: UnchangedSkipResult,
    processed: int,
    auto_approved: int,
    pending_review: int,
    newly_irrelevant: int,
    fetch_errors: int,
    classify_errors: int,
    emit: EmitFn,
) -> None:
    """Step 7 — Write ingestion run record + log summary."""
    updated_trials_count = len(buckets.updated_trials) - skip_result.clinical_skipped
    reeval_trials_count = len(buckets.reeval_list) - skip_result.rejected_skipped
    skipped_unchanged_count = skip_result.clinical_skipped + skip_result.rejected_skipped

    async with SessionLocal() as db:
        db.add(IngestionRun(
            run_at=datetime.utcnow(),
            search_terms=json.dumps(search_terms),
            candidates_found=len(all_candidates),
            new_trials=len(buckets.new_trials),
            updated_trials=updated_trials_count,
            reeval_trials=reeval_trials_count,
            relevant_processed=processed,
            irrelevant_processed=newly_irrelevant,
            fetch_errors=fetch_errors,
            classify_errors=classify_errors,
            skipped_unchanged=skipped_unchanged_count,
        ))
        await db.commit()

    final_summary = {
        "step": "complete",
        "label": "Done",
        "search_terms": search_terms,
        "candidates_found": len(all_candidates),
        "new": len(buckets.new_trials),
        "updated": updated_trials_count,
        "skipped_unchanged": skipped_unchanged_count,
        "reevaluated": reeval_trials_count,
        "relevant": processed,
        "auto_approved": auto_approved,
        "pending_review": pending_review,
        "irrelevant": newly_irrelevant,
        "fetch_errors": fetch_errors,
        "classify_errors": classify_errors,
    }
    await emit(final_summary)

    logger.info(
        "Ingestion complete: %d new, %d updated, %d skipped (unchanged), %d re-evaluated | "
        "%d relevant (%d auto-approved, %d pending review), %d irrelevant | "
        "%d fetch errors, %d classify failures (skipped, will retry next run) | "
        "search_terms=%s, total_candidates=%d",
        len(buckets.new_trials),
        updated_trials_count,
        skipped_unchanged_count,
        reeval_trials_count,
        processed,
        auto_approved,
        pending_review,
        newly_irrelevant,
        fetch_errors,
        classify_errors,
        search_terms,
        len(all_candidates),
    )

    await send_ingestion_summary(final_summary)


async def run_daily_ingestion(
    search_terms: List[str] | None = None,
    progress_callback: ProgressCallback = None,
):
    """Run one full ingestion pass; see PIPELINE OVERVIEW above for the steps."""
    if search_terms is None:
        search_terms = settings.SEARCH_TERMS

    emit = _make_emit(progress_callback)

    # ──────────────────────────────────────────────────────────
    # STEP 1 — Collect NCT IDs + last-update dates for each search term
    # ──────────────────────────────────────────────────────────
    all_candidates = await _collect_candidates(search_terms, emit)

    # ──────────────────────────────────────────────────────────
    # STEP 2 — Classify each NCT ID against our database
    # Three possible outcomes per candidate:
    #   new_trials     – NCT not in either table → fetch & process
    #   updated_trials – NCT in ClinicalTrial but date changed → re-fetch
    #   reeval_list    – NCT in IrrelevantTrial and date changed → re-evaluate
    # ──────────────────────────────────────────────────────────
    buckets = await _classify_candidates(all_candidates, emit)

    # ──────────────────────────────────────────────────────────
    # STEP 3 — Fetch full study data for all trials that need processing
    # ──────────────────────────────────────────────────────────
    trials_to_process = buckets.new_trials + buckets.updated_trials + buckets.reeval_list
    fetched, fetch_errors = await _fetch_trial_details(trials_to_process, emit)

    # Nothing survived the fetch: log the run, send the Step 8 summary, and stop
    # before touching the AI.
    if not fetched:
        await _record_empty_run(
            search_terms=search_terms,
            all_candidates=all_candidates,
            buckets=buckets,
            fetch_errors=fetch_errors,
            emit=emit,
        )
        return

    # ──────────────────────────────────────────────────────────
    # STEP 3.5 — Protect admin-edited custom_* fields on re-ingestion
    # Only trials that were previously in the DB may have admin-edited fields,
    # so we load state for the updated + re-evaluated buckets only. The
    # official_* snapshot loaded here is what Step 3.6 compares against.
    # ──────────────────────────────────────────────────────────
    trials_with_existing_edits = set(buckets.updated_trials) | set(buckets.reeval_list)
    existing_state = await load_existing_trial_state(
        SessionLocal, trials_with_existing_edits, fetched,
    )

    # ──────────────────────────────────────────────────────────
    # STEP 3.6 — Skip trials whose only changes are ignored fields
    # ClinicalTrials.gov frequently bumps last_update_post_date for
    # administrative touches (contact info, location adjustments) that have no
    # bearing on relevance or summary content. Those rows get their official_*
    # fields silently synced and drop out of `fetched` — no AI rerun, no status
    # reset — leaving only genuinely changed trials for Steps 4–6.
    # ──────────────────────────────────────────────────────────
    skip_result = await skip_unchanged_trials(
        SessionLocal,
        fetched,
        updated_trials=buckets.updated_trials,
        rejected_nct_ids=buckets.rejected_nct_ids,
        existing_state=existing_state,
        emit=emit,
    )
    fetched = skip_result.remaining_fetched

    # ──────────────────────────────────────────────────────────
    # STEP 4 — Relevance classification
    # AIClient is instantiated once per run (one connection pool) and reused by
    # Step 5. If OPENROUTER_API_KEY is not set, AIClient raises RuntimeError here.
    # ──────────────────────────────────────────────────────────
    ai_client = AIClient()
    classifications, failed_ids = await _classify_fetched_trials(
        fetched, ai_client, emit,
    )
    classify_errors = len(failed_ids)
    to_summarize, to_reject = _split_by_relevance(fetched, classifications, failed_ids)

    # ──────────────────────────────────────────────────────────
    # STEP 5 — AI summarisation: populate custom_* fields for relevant trials only
    # Admin-edited values from Step 3.5 win over anything the AI generates.
    # ──────────────────────────────────────────────────────────
    await _summarize_trials(
        to_summarize, ai_client, existing_state.custom_map, emit,
    )

    # ──────────────────────────────────────────────────────────
    # STEP 6 — Database upsert
    # to_summarize → clinical_trials (confident ⇒ APPROVED, unsure ⇒
    # PENDING_REVIEW), to_reject → irrelevant_trials. A trial that switched
    # tables has its row in the other table deleted.
    # ──────────────────────────────────────────────────────────
    processed, auto_approved, pending_review, newly_irrelevant = await _upsert_trials(
        to_summarize,
        to_reject,
        classifications=classifications,
        # ingestion_event: updated_trials are UPDATED, everything else is NEW.
        # Step 3.6's unchanged trials were already handled and dropped from `fetched`.
        updated_nct_ids=set(buckets.updated_trials),
        rejected_nct_ids=buckets.rejected_nct_ids,
        existing_approval_map=existing_state.approval_map,
        existing_snapshot_map=existing_state.snapshot_map,
    )

    # ──────────────────────────────────────────────────────────
    # STEP 7 — Write ingestion run record + log summary
    # STEP 8 — Email that same summary (sent from inside _record_ingestion_run)
    # ──────────────────────────────────────────────────────────
    await _record_ingestion_run(
        search_terms=search_terms,
        all_candidates=all_candidates,
        buckets=buckets,
        skip_result=skip_result,
        processed=processed,
        auto_approved=auto_approved,
        pending_review=pending_review,
        newly_irrelevant=newly_irrelevant,
        fetch_errors=fetch_errors,
        classify_errors=classify_errors,
        emit=emit,
    )


if __name__ == "__main__":
    asyncio.run(run_daily_ingestion())
