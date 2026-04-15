"""
Daily ingestion pipeline — syncs clinical trials from ClinicalTrials.gov.

Run once every N hours (configured via settings.INGESTION_SCHEDULE_HOURS,
scheduled by APScheduler in main.py).

PIPELINE OVERVIEW
=================
Step 1  Collect NCT IDs + last-update dates for each search term
Step 2  Classify each NCT ID against the database (new / updated / rejected / no-change)
Step 3  Fetch full trial data from ClinicalTrials.gov API v2
Step 4  Generate patient-friendly custom_* fields via AI summarisation
Step 5  Classify relevance with AI; upsert into clinical_trials or irrelevant_trials
Step 6  Re-evaluate previously rejected trials whose data has changed
Step 7  Log run summary

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
from typing import List

from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ClinicalTrial, IrrelevantTrial, TrialStatus
from app.services.ai.classifier import classify_trial
from app.services.ai.client import AIClient
from app.services.ai.summarizer import ai_generate_summaries
from app.services.ctgov import iter_study_index_rows
from app.services.ctgov.study_detail import fetch_full_study, map_api_to_model

logger = logging.getLogger(__name__)


async def run_daily_ingestion(
    search_terms: List[str] | None = None,
):
    if search_terms is None:
        search_terms = settings.SEARCH_TERMS

    # ──────────────────────────────────────────────────────────
    # STEP 1 — Collect NCT IDs + last-update dates for each term
    # ──────────────────────────────────────────────────────────
    # nct_id → last_update_posted_date (ISO 8601 string or "" if unknown)
    all_candidates: dict[str, str] = {}

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
    # STEP 6 prep — Determine which rejected trials need re-evaluation
    # (done here so reeval_list can extend trials_to_process before Step 3)
    # ──────────────────────────────────────────────────────────
    reeval_list = [
        nct_id
        for nct_id, api_date, stored_date in rejected_hits
        if api_date != (stored_date or "")
    ]

    # ──────────────────────────────────────────────────────────
    # STEP 3 — Fetch full study data for all trials that need processing
    # ──────────────────────────────────────────────────────────
    trials_to_process = new_trials + updated_trials + reeval_list
    fetched: list[dict] = []

    for nct_id in trials_to_process:
        raw = await asyncio.to_thread(fetch_full_study, nct_id)
        if raw is None:
            logger.warning("Skipping %s — fetch_full_study returned None", nct_id)
            continue
        fetched.append(map_api_to_model(raw))

    if not fetched:
        logger.info(
            "Ingestion complete: no trials to process "
            "(search_terms=%s, candidates=%d, new=%d, updated=%d, reeval=%d)",
            search_terms, len(all_candidates), len(new_trials),
            len(updated_trials), len(reeval_list),
        )
        return

    # ──────────────────────────────────────────────────────────
    # STEP 4 — AI summarisation: populate custom_* fields
    # AIClient is instantiated once per run (one connection pool).
    # If OPENAI_API_KEY is not set, AIClient raises RuntimeError here —
    # the ingestion run is aborted rather than silently writing null summaries.
    # ──────────────────────────────────────────────────────────
    ai_client = AIClient()

    for trial_data in fetched:
        custom_fields = await ai_generate_summaries(ai_client, trial_data)
        trial_data.update(custom_fields)

    # ──────────────────────────────────────────────────────────
    # STEP 5 — Relevance classification + database upsert
    # ──────────────────────────────────────────────────────────
    processed = 0
    newly_irrelevant = 0

    async with SessionLocal() as db:
        for trial_data in fetched:
            nct_id = trial_data.get("nct_id")

            try:
                classification = await classify_trial(ai_client, trial_data)
            except Exception as exc:
                logger.error("classify_trial raised for %s: %s", nct_id, exc)
                # Fail-safe: include for manual review rather than silently skip
                from app.services.ai.schemas import ClassificationResult, RelevanceTier
                classification = ClassificationResult(
                    is_relevant=True,
                    confidence=0.0,
                    reason=f"Classification error — needs manual review: {exc}",
                    relevance_tier=RelevanceTier.SECONDARY,
                    matching_criteria=["none"],
                )

            if classification.is_relevant:
                trial = ClinicalTrial(
                    **trial_data,
                    status=TrialStatus.PENDING_REVIEW,
                    ai_relevance_confidence=classification.confidence,
                    ai_relevance_reason=classification.reason,
                    ai_relevance_tier=classification.relevance_tier.value,
                    ai_matching_criteria=json.dumps(classification.matching_criteria),
                )
                await db.merge(trial)

                # If this trial was previously in irrelevant_trials, remove it
                if nct_id in [nct for nct, _, _ in rejected_hits]:
                    existing_irrelevant = await db.get(IrrelevantTrial, nct_id)
                    if existing_irrelevant:
                        await db.delete(existing_irrelevant)

                processed += 1
            else:
                irrelevant = IrrelevantTrial(
                    **trial_data,
                    irrelevance_reason=classification.reason,
                )
                await db.merge(irrelevant)

                # If this trial was previously in clinical_trials, remove it
                existing_clinical = await db.get(ClinicalTrial, nct_id)
                if existing_clinical:
                    await db.delete(existing_clinical)
                newly_irrelevant += 1

        await db.commit()

    # ──────────────────────────────────────────────────────────
    # STEP 7 — Log run summary
    # ──────────────────────────────────────────────────────────
    logger.info(
        "Ingestion complete: %d new, %d updated, %d re-evaluated | "
        "%d relevant (PENDING_REVIEW), %d irrelevant | "
        "search_terms=%s, total_candidates=%d",
        len(new_trials),
        len(updated_trials),
        len(reeval_list),
        processed,
        newly_irrelevant,
        search_terms,
        len(all_candidates),
    )


if __name__ == "__main__":
    asyncio.run(run_daily_ingestion())
