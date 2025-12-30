import asyncio
import random

from app.db.database import SessionLocal
from app.db.models import ClinicalTrial, TrialStatus


async def run_daily_ingestion():
    print("Fetching trials from ClinicalTrials.gov...")
    # Simulate API latency
    await asyncio.sleep(1)

    print("Generating AI summaries...")
    await asyncio.sleep(1)

    # Create a dummy record
    async with SessionLocal() as session:
        # Check if we already have some dummy data to avoid spamming
        # on every restart/run
        # For demo purposes, we'll just add one.

        nct_id = f"NCT{random.randint(100000, 999999)}"

        new_trial = ClinicalTrial(
            nct_id=nct_id,
            title=f"Study of Osteosarcoma Treatment {nct_id}",
            official_summary=(
                "This is the official raw summary from the government database."
            ),
            custom_summary="AI Generated simplified summary.",
            status=TrialStatus.PENDING_REVIEW,
        )

        session.add(new_trial)
        await session.commit()
        print(f"Ingested new trial: {nct_id} with status PENDING_REVIEW")
