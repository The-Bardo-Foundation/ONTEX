from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalTrial, IngestionEvent, TrialStatus

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────────────────────────────────────

class TrialUpdate(BaseModel):
    status: TrialStatus
    custom_brief_summary: Optional[str] = None


class TrialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nct_id: str
    brief_title: str
    brief_summary: Optional[str]
    custom_brief_summary: Optional[str]
    status: TrialStatus
    ingestion_event: Optional[IngestionEvent] = None


class TrialListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nct_id: str
    brief_title: str
    phase: Optional[str]
    status: TrialStatus
    ingestion_event: Optional[IngestionEvent]
    last_update_post_date: Optional[str]


class TrialDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nct_id: str
    status: TrialStatus
    ingestion_event: Optional[IngestionEvent]

    # Official fields
    brief_title: str
    brief_summary: Optional[str]
    overall_status: Optional[str]
    phase: Optional[str]
    study_type: Optional[str]
    location_country: Optional[str]
    location_city: Optional[str]
    minimum_age: Optional[str]
    maximum_age: Optional[str]
    central_contact_name: Optional[str]
    central_contact_phone: Optional[str]
    central_contact_email: Optional[str]
    eligibility_criteria: Optional[str]
    intervention_description: Optional[str]
    last_update_post_date: Optional[str]
    key_information: Optional[str]

    # Custom (AI/admin) fields
    custom_brief_title: Optional[str]
    custom_brief_summary: Optional[str]
    custom_overall_status: Optional[str]
    custom_phase: Optional[str]
    custom_study_type: Optional[str]
    custom_location_country: Optional[str]
    custom_location_city: Optional[str]
    custom_minimum_age: Optional[str]
    custom_maximum_age: Optional[str]
    custom_central_contact_name: Optional[str]
    custom_central_contact_phone: Optional[str]
    custom_central_contact_email: Optional[str]
    custom_eligibility_criteria: Optional[str]
    custom_intervention_description: Optional[str]
    custom_last_update_post_date: Optional[str]

    # AI classification
    ai_relevance_confidence: Optional[float]
    ai_relevance_reason: Optional[str]
    ai_relevance_tier: Optional[str]
    ai_matching_criteria: Optional[str]  # JSON string

    # Workflow tracking
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    previous_approved_at: Optional[datetime]
    previous_approved_by: Optional[str]
    rejected_at: Optional[datetime]
    rejected_by: Optional[str]
    reviewer_notes: Optional[str]
    previous_official_snapshot: Optional[str]  # JSON string


_CUSTOM_FIELDS = [
    "custom_brief_title", "custom_brief_summary", "custom_overall_status",
    "custom_phase", "custom_study_type", "custom_location_country",
    "custom_location_city", "custom_minimum_age", "custom_maximum_age",
    "custom_central_contact_name", "custom_central_contact_phone",
    "custom_central_contact_email", "custom_eligibility_criteria",
    "custom_intervention_description", "custom_last_update_post_date",
    "key_information",
]


class ApproveBody(BaseModel):
    username: str = Field(min_length=1)
    reviewer_notes: Optional[str] = None
    # All editable fields the reviewer may have updated in the review panel
    custom_brief_title: Optional[str] = None
    custom_brief_summary: Optional[str] = None
    custom_overall_status: Optional[str] = None
    custom_phase: Optional[str] = None
    custom_study_type: Optional[str] = None
    custom_location_country: Optional[str] = None
    custom_location_city: Optional[str] = None
    custom_minimum_age: Optional[str] = None
    custom_maximum_age: Optional[str] = None
    custom_central_contact_name: Optional[str] = None
    custom_central_contact_phone: Optional[str] = None
    custom_central_contact_email: Optional[str] = None
    custom_eligibility_criteria: Optional[str] = None
    custom_intervention_description: Optional[str] = None
    custom_last_update_post_date: Optional[str] = None
    key_information: Optional[str] = None


class RejectBody(BaseModel):
    username: str = Field(min_length=1)
    reviewer_notes: Optional[str] = None


class TrialsListResponse(BaseModel):
    items: List[TrialListItem]
    total: int
    page: int
    page_size: int


# ──────────────────────────────────────────────────────────────────────────────
# WordPress / PHP template models (unchanged)
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# NOTE: /trials/review-queue must be registered before /trials/{nct_id}
# so FastAPI does not match the literal "review-queue" as a path parameter.
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/trials/review-queue", response_model=List[TrialListItem])
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """Return all PENDING_REVIEW trials, ordered by last update date."""
    stmt = (
        select(ClinicalTrial)
        .where(ClinicalTrial.status == TrialStatus.PENDING_REVIEW)
        .order_by(ClinicalTrial.last_update_post_date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/trials", response_model=TrialsListResponse)
async def get_trials(
    status: Optional[TrialStatus] = None,
    q: Optional[str] = None,
    ingestion_event: Optional[IngestionEvent] = None,
    sort_by: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List trials with optional filtering, full-text search, sorting, and pagination.

    - q: case-insensitive search across brief_title, brief_summary, eligibility_criteria
    - status: filter by PENDING_REVIEW / APPROVED / REJECTED
    - ingestion_event: filter by NEW / UPDATED
    - sort_by: "last_update_post_date" (default, desc) or "brief_title" (asc)
    - page / page_size: 1-based pagination
    """
    stmt = select(ClinicalTrial)

    if status:
        stmt = stmt.where(ClinicalTrial.status == status)
    if ingestion_event:
        stmt = stmt.where(ClinicalTrial.ingestion_event == ingestion_event)
    if q:
        stmt = stmt.where(
            or_(
                ClinicalTrial.brief_title.ilike(f"%{q}%"),
                ClinicalTrial.brief_summary.ilike(f"%{q}%"),
                ClinicalTrial.eligibility_criteria.ilike(f"%{q}%"),
            )
        )

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    # Sort
    if sort_by == "brief_title":
        stmt = stmt.order_by(ClinicalTrial.brief_title.asc())
    else:
        stmt = stmt.order_by(ClinicalTrial.last_update_post_date.desc())

    # Paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = result.scalars().all()

    return TrialsListResponse(items=items, total=total or 0, page=page, page_size=page_size)


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


@router.get("/trials/{nct_id}", response_model=TrialDetail)
async def get_trial(nct_id: str, db: AsyncSession = Depends(get_db)):
    """Return full trial detail for a single trial."""
    stmt = select(ClinicalTrial).where(ClinicalTrial.nct_id == nct_id)
    result = await db.execute(stmt)
    trial = result.scalars().first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@router.patch("/trials/{nct_id}/approve", response_model=TrialDetail)
async def approve_trial(nct_id: str, body: ApproveBody, db: AsyncSession = Depends(get_db)):
    """
    Approve a trial.  Sets status=APPROVED, records approved_by/approved_at,
    and applies any custom field edits submitted alongside the approval.
    """
    stmt = select(ClinicalTrial).where(ClinicalTrial.nct_id == nct_id)
    result = await db.execute(stmt)
    trial = result.scalars().first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    trial.status = TrialStatus.APPROVED
    trial.approved_at = datetime.utcnow()
    trial.approved_by = body.username
    trial.reviewer_notes = body.reviewer_notes

    for field in _CUSTOM_FIELDS:
        value = getattr(body, field, None)
        if value is not None:
            setattr(trial, field, value)

    await db.commit()
    await db.refresh(trial)
    return trial


@router.patch("/trials/{nct_id}/reject", response_model=TrialDetail)
async def reject_trial(nct_id: str, body: RejectBody, db: AsyncSession = Depends(get_db)):
    """Reject a trial.  Sets status=REJECTED and records rejected_by/rejected_at."""
    stmt = select(ClinicalTrial).where(ClinicalTrial.nct_id == nct_id)
    result = await db.execute(stmt)
    trial = result.scalars().first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    trial.status = TrialStatus.REJECTED
    trial.rejected_at = datetime.utcnow()
    trial.rejected_by = body.username
    trial.reviewer_notes = body.reviewer_notes

    await db.commit()
    await db.refresh(trial)
    return trial


@router.patch("/trials/{nct_id}", response_model=TrialResponse)
async def update_trial(
    nct_id: str, body: TrialUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update trial status and custom summary.
    Kept for backwards compatibility with existing tests.
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
