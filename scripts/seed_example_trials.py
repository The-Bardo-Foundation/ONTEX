"""Seed the database with example trials for local development.

Inserts a small, varied set of trials covering each review status and AI label so
the UI has data to render in the review queue, public viewer, and irrelevant-trials
views. NCT IDs are prefixed NCT99999XXX so they cannot collide with real trials
from a future ingestion.

Idempotent: re-running upserts on nct_id.

Run from the repo root:
    python scripts/seed_example_trials.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.database import SessionLocal, engine
from app.db.models import (
    ClinicalTrial,
    IngestionEvent,
    IrrelevantTrial,
    TrialStatus,
)


NOW = datetime.utcnow()


RELEVANT_TRIALS = [
    {
        "nct_id": "NCT99999001",
        "brief_title": "Phase II Trial of Mifamurtide in Pediatric High-Grade Osteosarcoma",
        "brief_summary": (
            "This study evaluates the efficacy and safety of mifamurtide combined with "
            "standard MAP chemotherapy in newly diagnosed pediatric patients with "
            "high-grade osteosarcoma."
        ),
        "overall_status": "RECRUITING",
        "phase": "PHASE2",
        "study_type": "INTERVENTIONAL",
        "location_country": "United States",
        "location_city": "Boston",
        "minimum_age": "5 Years",
        "maximum_age": "30 Years",
        "central_contact_name": "Dr. Jane Doe",
        "central_contact_email": "trials@example.org",
        "eligibility_criteria": "Histologically confirmed high-grade osteosarcoma. Age 5-30 years.",
        "intervention_description": "Mifamurtide 2 mg/m^2 IV twice weekly plus MAP backbone.",
        "last_update_post_date": "2026-04-15",
        "status": TrialStatus.PENDING_REVIEW,
        "ai_relevance_label": "RELEVANT",
        "ai_relevance_reason": "Phase II interventional study in osteosarcoma — clear match.",
        "ingestion_event": IngestionEvent.NEW,
    },
    {
        "nct_id": "NCT99999002",
        "brief_title": "Immunotherapy with Pembrolizumab in Recurrent Osteosarcoma",
        "brief_summary": (
            "A single-arm study assessing pembrolizumab monotherapy in adolescents and "
            "young adults with relapsed or refractory osteosarcoma."
        ),
        "overall_status": "RECRUITING",
        "phase": "PHASE1",
        "study_type": "INTERVENTIONAL",
        "location_country": "Germany",
        "location_city": "Berlin",
        "minimum_age": "12 Years",
        "maximum_age": "40 Years",
        "central_contact_name": "Dr. Hans Müller",
        "central_contact_email": "osteo-trial@charite.example",
        "eligibility_criteria": "Relapsed or refractory osteosarcoma after at least one line of therapy.",
        "intervention_description": "Pembrolizumab 200 mg IV every 3 weeks.",
        "last_update_post_date": "2026-05-02",
        "status": TrialStatus.APPROVED,
        "ai_relevance_label": "RELEVANT",
        "ai_relevance_reason": "Immunotherapy trial specifically in recurrent osteosarcoma.",
        "approved_at": NOW - timedelta(days=3),
        "approved_by": "reviewer@bardo.example",
        "reviewer_notes": "High patient interest — prioritize for newsletter.",
        "ingestion_event": IngestionEvent.NEW,
    },
    {
        "nct_id": "NCT99999003",
        "brief_title": "Surgical Margin Assessment with Intraoperative Imaging in Osteosarcoma",
        "brief_summary": (
            "Observational study evaluating a novel intraoperative imaging modality "
            "for assessing surgical margins during limb-salvage osteosarcoma resections."
        ),
        "overall_status": "ACTIVE_NOT_RECRUITING",
        "phase": "NA",
        "study_type": "OBSERVATIONAL",
        "location_country": "Norway",
        "location_city": "Oslo",
        "minimum_age": "10 Years",
        "maximum_age": "65 Years",
        "central_contact_name": "Dr. Astrid Berg",
        "central_contact_email": "ous-osteo@example.no",
        "eligibility_criteria": "Patients undergoing surgical resection for primary osteosarcoma.",
        "intervention_description": "Intraoperative fluorescence imaging during resection.",
        "last_update_post_date": "2026-03-21",
        "status": TrialStatus.PENDING_REVIEW,
        "ai_relevance_label": "UNCERTAIN",
        "ai_relevance_reason": "Surgical/imaging focus rather than therapeutic intervention — needs human review.",
        "ingestion_event": IngestionEvent.UPDATED,
    },
    {
        "nct_id": "NCT99999004",
        "brief_title": "Long-Term Cardiac Follow-Up After Doxorubicin in Osteosarcoma Survivors",
        "brief_summary": (
            "Prospective cohort study following adult survivors of childhood osteosarcoma "
            "for late cardiac effects of doxorubicin-based chemotherapy."
        ),
        "overall_status": "ENROLLING_BY_INVITATION",
        "phase": "NA",
        "study_type": "OBSERVATIONAL",
        "location_country": "United Kingdom",
        "location_city": "London",
        "minimum_age": "18 Years",
        "maximum_age": "N/A",
        "central_contact_name": "Dr. Emma Clarke",
        "central_contact_email": "survivorship@example.uk",
        "eligibility_criteria": "Adults treated for osteosarcoma in childhood with doxorubicin-containing regimens.",
        "intervention_description": "Annual echocardiogram and cardiac MRI.",
        "last_update_post_date": "2026-02-10",
        "status": TrialStatus.APPROVED,
        "ai_relevance_label": "RELEVANT",
        "ai_relevance_reason": "Survivorship study in osteosarcoma population.",
        "approved_at": NOW - timedelta(days=20),
        "approved_by": "reviewer@bardo.example",
        "ingestion_event": IngestionEvent.NEW,
    },
]


IRRELEVANT_TRIALS = [
    {
        "nct_id": "NCT99999101",
        "brief_title": "Osteoporosis Risk Factors in Postmenopausal Women",
        "brief_summary": "Epidemiological study of osteoporosis risk factors — not osteosarcoma.",
        "overall_status": "COMPLETED",
        "phase": "NA",
        "study_type": "OBSERVATIONAL",
        "location_country": "France",
        "location_city": "Paris",
        "last_update_post_date": "2026-01-08",
        "ai_relevance_label": "IRRELEVANT",
        "ai_relevance_reason": "Study concerns osteoporosis, not osteosarcoma — keyword match only.",
        "rejected_at": NOW - timedelta(days=10),
        "rejected_by": None,  # AI rejection
        "ingestion_event": IngestionEvent.NEW,
    },
    {
        "nct_id": "NCT99999102",
        "brief_title": "Ewing Sarcoma Combination Chemotherapy Dose Escalation",
        "brief_summary": "Phase I dose-escalation study in Ewing sarcoma.",
        "overall_status": "RECRUITING",
        "phase": "PHASE1",
        "study_type": "INTERVENTIONAL",
        "location_country": "Italy",
        "location_city": "Milan",
        "last_update_post_date": "2026-04-30",
        "ai_relevance_label": "RELEVANT",
        "ai_relevance_reason": "Sarcoma trial — flagged as potentially relevant by AI.",
        "rejected_at": NOW - timedelta(days=2),
        "rejected_by": "reviewer@bardo.example",
        "reviewer_notes": "Ewing sarcoma, not osteosarcoma — out of scope.",
        "ingestion_event": IngestionEvent.NEW,
    },
]


async def upsert(session, model, rows):
    """Upsert rows on primary key (nct_id). Picks dialect-appropriate ON CONFLICT."""
    dialect = engine.dialect.name
    for row in rows:
        if dialect == "postgresql":
            stmt = pg_insert(model).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["nct_id"],
                set_={k: v for k, v in row.items() if k != "nct_id"},
            )
        elif dialect == "sqlite":
            stmt = sqlite_insert(model).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["nct_id"],
                set_={k: v for k, v in row.items() if k != "nct_id"},
            )
        else:
            raise RuntimeError(f"Unsupported dialect for seed: {dialect}")
        await session.execute(stmt)


async def main():
    async with SessionLocal() as session:
        await upsert(session, ClinicalTrial, RELEVANT_TRIALS)
        await upsert(session, IrrelevantTrial, IRRELEVANT_TRIALS)
        await session.commit()
    print(
        f"Seeded {len(RELEVANT_TRIALS)} clinical_trials and "
        f"{len(IRRELEVANT_TRIALS)} irrelevant_trials."
    )


if __name__ == "__main__":
    asyncio.run(main())
