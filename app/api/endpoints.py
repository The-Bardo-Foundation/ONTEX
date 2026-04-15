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
    custom_brief_summary: Optional[str] = None


class TrialResponse(BaseModel):
    nct_id: str
    brief_title: str
    brief_summary: Optional[str]
    custom_brief_summary: Optional[str]
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


class PhpTrialResult(BaseModel):
    NCTId: str
    BriefTitle: Optional[str] = None
    CustomBriefTitle: Optional[str] = None
    BriefSummary: Optional[str] = None
    CustomBriefSummary: Optional[str] = None
    OverallStatus: Optional[str] = None
    CustomOverallStatus: Optional[str] = None
    Phase: Optional[str] = None
    CustomPhase: Optional[str] = None
    StudyType: Optional[str] = None
    CustomStudyType: Optional[str] = None
    LocationCountry: Optional[str] = None
    CustomLocationCountry: Optional[str] = None
    LocationCity: Optional[str] = None
    CustomLocationCity: Optional[str] = None
    MinimumAge: Optional[str] = None
    CustomMinimumAge: Optional[str] = None
    MaximumAge: Optional[str] = None
    CustomMaximumAge: Optional[str] = None
    CentralContactName: Optional[str] = None
    CustomCentralContactName: Optional[str] = None
    CentralContactPhone: Optional[str] = None
    CustomCentralContactPhone: Optional[str] = None
    CentralContactEMail: Optional[str] = None
    CustomCentralContactEMail: Optional[str] = None
    EligibilityCriteria: Optional[str] = None
    CustomEligibilityCriteria: Optional[str] = None
    InterventionDescription: Optional[str] = None
    CustomInterventionDescription: Optional[str] = None
    LastUpdatePostDate: Optional[str] = None
    CustomLastUpdatePostDate: Optional[str] = None
    key_information: Optional[str] = None


class PhpTrialResponse(BaseModel):
    result: List[PhpTrialResult]


@router.get("/trail", response_model=PhpTrialResponse)
async def get_trail(trail_id: str, db: AsyncSession = Depends(get_db)):
    """WordPress PHP template endpoint — returns an approved trial in legacy PascalCase format."""
    stmt = select(ClinicalTrial).where(
        ClinicalTrial.nct_id == trail_id,
        ClinicalTrial.status == TrialStatus.APPROVED,
    )
    result = await db.execute(stmt)
    trial = result.scalars().first()

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    return PhpTrialResponse(result=[PhpTrialResult(
        NCTId=trial.nct_id,
        BriefTitle=trial.brief_title,
        CustomBriefTitle=trial.custom_brief_title,
        BriefSummary=trial.brief_summary,
        CustomBriefSummary=trial.custom_brief_summary,
        OverallStatus=trial.overall_status,
        CustomOverallStatus=trial.custom_overall_status,
        Phase=trial.phase,
        CustomPhase=trial.custom_phase,
        StudyType=trial.study_type,
        CustomStudyType=trial.custom_study_type,
        LocationCountry=trial.location_country,
        CustomLocationCountry=trial.custom_location_country,
        LocationCity=trial.location_city,
        CustomLocationCity=trial.custom_location_city,
        MinimumAge=trial.minimum_age,
        CustomMinimumAge=trial.custom_minimum_age,
        MaximumAge=trial.maximum_age,
        CustomMaximumAge=trial.custom_maximum_age,
        CentralContactName=trial.central_contact_name,
        CustomCentralContactName=trial.custom_central_contact_name,
        CentralContactPhone=trial.central_contact_phone,
        CustomCentralContactPhone=trial.custom_central_contact_phone,
        CentralContactEMail=trial.central_contact_email,
        CustomCentralContactEMail=trial.custom_central_contact_email,
        EligibilityCriteria=trial.eligibility_criteria,
        CustomEligibilityCriteria=trial.custom_eligibility_criteria,
        InterventionDescription=trial.intervention_description,
        CustomInterventionDescription=trial.custom_intervention_description,
        LastUpdatePostDate=trial.last_update_post_date,
        CustomLastUpdatePostDate=trial.custom_last_update_post_date,
        key_information=trial.key_information,
    )])


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
    if body.custom_brief_summary is not None:
        trial.custom_brief_summary = body.custom_brief_summary

    await db.commit()
    await db.refresh(trial)
    return trial
