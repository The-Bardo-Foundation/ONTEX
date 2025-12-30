from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalTrial, TrialStatus

router = APIRouter()


class TrialUpdate(BaseModel):
    status: TrialStatus
    custom_summary: Optional[str] = None


class TrialResponse(BaseModel):
    id: int
    nct_id: str
    title: str
    official_summary: str
    custom_summary: Optional[str]
    status: TrialStatus

    class Config:
        from_attributes = True


@router.get("/trials", response_model=List[TrialResponse])
async def get_trials(
    status: Optional[TrialStatus] = None, db: AsyncSession = Depends(get_db)
):
    """
    Get trials, optionally filtered by status.
    """
    stmt = select(ClinicalTrial)
    if status:
        stmt = stmt.where(ClinicalTrial.status == status)

    result = await db.execute(stmt)
    trials = result.scalars().all()
    return trials


@router.patch("/trials/{nct_id}", response_model=TrialResponse)
async def update_trial(
    nct_id: str, body: TrialUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update trial status and custom summary.
    """
    stmt = select(ClinicalTrial).where(ClinicalTrial.nct_id == nct_id)
    result = await db.execute(stmt)
    trial = result.scalars().first()

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    trial.status = body.status
    if body.custom_summary is not None:
        trial.custom_summary = body.custom_summary

    await db.commit()
    await db.refresh(trial)
    return trial
