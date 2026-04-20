import asyncio
import copy
import json
import re
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.middleware import clerk_user, optional_clerk_user
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ClinicalTrial, IngestionEvent, IngestionRun, IrrelevantTrial, TrialStatus

router = APIRouter()

# ── Ingestion background-job state ────────────────────────────────────────────
# asyncio.Lock() is the right tool here: Railway runs a single process/replica,
# so an in-process lock is sufficient and avoids the connection-lifetime problem
# of PostgreSQL advisory locks (which are released when the request session
# closes, making them useless for a detached background task).

_ingestion_lock = asyncio.Lock()

_STEP_TEMPLATE: list[dict[str, Any]] = [
    {"id": "searching",        "label": "Searching ClinicalTrials.gov", "state": "waiting", "count": None, "total": None, "note": None},
    {"id": "fetching_details", "label": "Fetching trial details",        "state": "waiting", "count": None, "total": None, "note": None},
    {"id": "classifying",      "label": "AI classification",             "state": "waiting", "count": None, "total": None, "note": None},
    {"id": "summarizing",      "label": "Generating summaries",          "state": "waiting", "count": None, "total": None, "note": None},
]

_ingestion_status: dict[str, Any] = {
    "running": False,
    "steps": copy.deepcopy(_STEP_TEMPLATE),
    "error": None,
    "summary": None,
}


def _find_step(step_id: str) -> dict:
    for s in _ingestion_status["steps"]:
        if s["id"] == step_id:
            return s
    raise KeyError(step_id)


async def _ingestion_progress_callback(event: dict) -> None:
    step_id = event.get("step")
    if step_id == "searching":
        _find_step("searching")["state"] = "active"
    elif step_id == "searching_done":
        s = _find_step("searching")
        s["state"] = "done"
        s["note"] = f"{event.get('count', 0):,} candidates found"
    elif step_id in ("fetching_details", "classifying", "summarizing"):
        s = _find_step(step_id)
        s["state"] = "active"
        s["count"] = event.get("count")
        s["total"] = event.get("total")
    elif step_id == "complete":
        for s in _ingestion_status["steps"]:
            if s["state"] == "active":
                s["state"] = "done"
        _ingestion_status["summary"] = event
        _ingestion_status["running"] = False
    elif step_id == "error":
        _ingestion_status["error"] = event.get("message", "Unknown error")
        _ingestion_status["running"] = False

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
    overall_status: Optional[str]
    brief_summary: Optional[str]
    custom_brief_summary: Optional[str]
    status: TrialStatus
    ingestion_event: Optional[IngestionEvent]
    last_update_post_date: Optional[str]
    ai_relevance_label: Optional[str]
    location_country: Optional[str]
    location_city: Optional[str]
    custom_location_country: Optional[str]
    custom_location_city: Optional[str]


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
    ai_relevance_label: Optional[str]
    ai_relevance_reason: Optional[str]

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
    username: Optional[str] = None  # Ignored server-side; kept for API backwards-compat
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
    username: Optional[str] = None  # Ignored server-side; kept for API backwards-compat
    reviewer_notes: Optional[str] = None


class TrialsListResponse(BaseModel):
    items: List[TrialListItem]
    total: int
    page: int
    page_size: int


class IrrelevantTrialListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nct_id: str
    brief_title: str
    phase: Optional[str]
    overall_status: Optional[str]
    brief_summary: Optional[str]
    last_update_post_date: Optional[str]
    irrelevance_reason: Optional[str]


class IrrelevantTrialsListResponse(BaseModel):
    items: List[IrrelevantTrialListItem]
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

class TrialFacets(BaseModel):
    countries: List[str]


@router.get("/trials/facets", response_model=TrialFacets)
async def get_trial_facets(db: AsyncSession = Depends(get_db)):
    """
    Return distinct filterable values from approved trials.

    - countries: sorted list of individual country names (split from comma-joined location_country)
    """
    country_field = func.coalesce(
        ClinicalTrial.custom_location_country,
        ClinicalTrial.location_country,
    )
    stmt = (
        select(country_field)
        .where(
            ClinicalTrial.status == TrialStatus.APPROVED,
            country_field.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    raw_countries = [row[0] for row in result.fetchall()]

    # location_country may be comma-joined (e.g. "United States, Norway")
    unique: set[str] = set()
    for entry in raw_countries:
        for country in entry.split(","):
            country = country.strip()
            if country:
                unique.add(country)

    return TrialFacets(countries=sorted(unique))


@router.get("/trials/review-queue", response_model=List[TrialListItem])
async def get_review_queue(
    _user: dict = Depends(clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all PENDING_REVIEW trials, ordered by last update date."""
    stmt = (
        select(ClinicalTrial)
        .where(ClinicalTrial.status == TrialStatus.PENDING_REVIEW)
        .order_by(ClinicalTrial.last_update_post_date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


_RECRUITING_NOW = ["RECRUITING"]
_NOT_RECRUITING = ["NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"]
_FINISHED = ["COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"]

# ── Age filtering helpers ──────────────────────────────────────────────────────
# minimum_age / maximum_age are free-text strings from ClinicalTrials.gov,
# e.g. "18 Years", "6 Months", "N/A". We parse them in Python because SQLite
# cannot reliably extract numbers from arbitrary strings.

def _parse_age_years(age_str: Optional[str]) -> Optional[float]:
    """Return age in years, or None if unknown / N/A (meaning no restriction)."""
    if not age_str or age_str.strip().upper() in ("N/A", ""):
        return None
    m = re.match(r"(\d+(?:\.\d+)?)\s*(year|month|week|day)", age_str.strip(), re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("month"):
        value /= 12
    elif unit.startswith("week"):
        value /= 52
    elif unit.startswith("day"):
        value /= 365
    return value


def _matches_age_group(trial: "ClinicalTrial", age_group: str) -> bool:
    """Return True if a person in the given age group is eligible for this trial."""
    min_age = _parse_age_years(trial.minimum_age)   # None = no lower bound
    max_age = _parse_age_years(trial.maximum_age)   # None = no upper bound
    if age_group == "child":        # under-18 eligible
        return (min_age is None or min_age < 18) and (max_age is None or max_age >= 1)
    if age_group == "adult":        # 18–64 eligible
        return (min_age is None or min_age <= 64) and (max_age is None or max_age >= 18)
    if age_group == "older_adult":  # 65+ eligible
        return (min_age is None or min_age <= 65) and (max_age is None or max_age >= 65)
    return True


@router.get("/trials", response_model=TrialsListResponse)
async def get_trials(
    status: Optional[TrialStatus] = None,
    q: Optional[str] = None,
    ingestion_event: Optional[IngestionEvent] = None,
    phase: Optional[str] = None,
    recruiting_status: Optional[str] = None,
    country: Optional[str] = None,
    age_group: Optional[str] = None,
    sort_by: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    clerk_user_claims: Optional[dict] = Depends(optional_clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List trials with optional filtering, full-text search, sorting, and pagination.

    - q: case-insensitive search across brief_title, brief_summary, eligibility_criteria
    - status: filter by PENDING_REVIEW / APPROVED / REJECTED
    - ingestion_event: filter by NEW / UPDATED
    - phase: substring match on phase field (e.g. "PHASE1" matches "PHASE1" and "PHASE1_PHASE2")
    - recruiting_status: "recruiting" | "not_recruiting" | "finished"
    - country: substring match on location_country (handles comma-joined multi-country values)
    - age_group: "child" | "adult" | "older_adult" — Python-side filter (age strings can't be compared in SQL)
    - sort_by: "last_update_post_date" (default, desc) or "brief_title" (asc)
    - page / page_size: 1-based pagination
    """
    stmt = select(ClinicalTrial)
    is_authenticated = clerk_user_claims is not None

    if not is_authenticated:
        stmt = stmt.where(ClinicalTrial.status == TrialStatus.APPROVED)
    elif status:
        stmt = stmt.where(ClinicalTrial.status == status)

    if ingestion_event and is_authenticated:
        stmt = stmt.where(ClinicalTrial.ingestion_event == ingestion_event)
    if phase:
        stmt = stmt.where(ClinicalTrial.phase.ilike(f"%{phase}%"))
    if recruiting_status == "recruiting":
        stmt = stmt.where(ClinicalTrial.overall_status.in_(_RECRUITING_NOW))
    elif recruiting_status == "not_recruiting":
        stmt = stmt.where(ClinicalTrial.overall_status.in_(_NOT_RECRUITING))
    elif recruiting_status == "finished":
        stmt = stmt.where(ClinicalTrial.overall_status.in_(_FINISHED))
    if country:
        stmt = stmt.where(ClinicalTrial.location_country.ilike(f"%{country}%"))
    if q:
        stmt = stmt.where(
            or_(
                ClinicalTrial.brief_title.ilike(f"%{q}%"),
                ClinicalTrial.brief_summary.ilike(f"%{q}%"),
                ClinicalTrial.eligibility_criteria.ilike(f"%{q}%"),
            )
        )

    # Sort
    if sort_by == "brief_title":
        stmt = stmt.order_by(ClinicalTrial.brief_title.asc())
    else:
        stmt = stmt.order_by(ClinicalTrial.last_update_post_date.desc())

    if age_group:
        # Age strings can't be compared reliably in SQL — fetch all matches and
        # filter + paginate in Python. Fine for the small trial sets we have.
        result = await db.execute(stmt)
        all_items = [t for t in result.scalars().all() if _matches_age_group(t, age_group)]
        total = len(all_items)
        items = all_items[(page - 1) * page_size : page * page_size]
    else:
        # Standard DB-level count + paginate
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        items = result.scalars().all()

    return TrialsListResponse(items=items, total=total or 0, page=page, page_size=page_size)


@router.get("/irrelevant-trials", response_model=IrrelevantTrialsListResponse)
async def get_irrelevant_trials(
    q: Optional[str] = None,
    sort_by: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _user: dict = Depends(clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """List irrelevant trials (AI-rejected) with search, sorting, and pagination. Admin only."""
    stmt = select(IrrelevantTrial)

    if q:
        stmt = stmt.where(
            or_(
                IrrelevantTrial.brief_title.ilike(f"%{q}%"),
                IrrelevantTrial.brief_summary.ilike(f"%{q}%"),
            )
        )

    if sort_by == "brief_title":
        stmt = stmt.order_by(IrrelevantTrial.brief_title.asc())
    else:
        stmt = stmt.order_by(IrrelevantTrial.last_update_post_date.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return IrrelevantTrialsListResponse(items=items, total=total or 0, page=page, page_size=page_size)


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
async def approve_trial(
    nct_id: str,
    body: ApproveBody,
    _user: dict = Depends(clerk_user),
    db: AsyncSession = Depends(get_db),
):
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
    trial.approved_by = _user.get("email") or _user.get("sub")
    trial.reviewer_notes = body.reviewer_notes

    for field in _CUSTOM_FIELDS:
        value = getattr(body, field, None)
        if value is not None:
            setattr(trial, field, value)

    await db.commit()
    await db.refresh(trial)
    return trial


@router.patch("/trials/{nct_id}/reject", response_model=TrialDetail)
async def reject_trial(
    nct_id: str,
    body: RejectBody,
    _user: dict = Depends(clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a trial.  Sets status=REJECTED and records rejected_by/rejected_at."""
    stmt = select(ClinicalTrial).where(ClinicalTrial.nct_id == nct_id)
    result = await db.execute(stmt)
    trial = result.scalars().first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    trial.status = TrialStatus.REJECTED
    trial.rejected_at = datetime.utcnow()
    trial.rejected_by = _user.get("email") or _user.get("sub")
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


# ──────────────────────────────────────────────────────────────────────────────
# Ingestion endpoints (fire-and-forget + polling)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/ingestion/start")
async def start_ingestion(_user: dict = Depends(clerk_user)):
    """
    Start the ingestion pipeline as a detached background task.

    Returns 200 {"started": true} immediately, or 409 if a run is already
    in progress. Poll GET /ingestion/status every ~2 s for progress updates.
    """
    if _ingestion_lock.locked():
        raise HTTPException(status_code=409, detail="Ingestion already running")

    _ingestion_status["running"] = True
    _ingestion_status["steps"] = copy.deepcopy(_STEP_TEMPLATE)
    _ingestion_status["error"] = None
    _ingestion_status["summary"] = None

    async def _run() -> None:
        async with _ingestion_lock:
            try:
                import app.services.ingestion as ingestion
                await ingestion.run_daily_ingestion(
                    progress_callback=_ingestion_progress_callback
                )
            except Exception as exc:
                _ingestion_status["error"] = str(exc)
                _ingestion_status["running"] = False

    asyncio.create_task(_run())
    return {"started": True}


@router.get("/ingestion/status")
async def get_ingestion_status(_user: dict = Depends(clerk_user)):
    """Return current ingestion pipeline status for frontend polling."""
    return copy.deepcopy(_ingestion_status)


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_at: datetime
    candidates_found: int
    new_trials: int
    updated_trials: int
    reeval_trials: int
    relevant_processed: int
    irrelevant_processed: int
    fetch_errors: int
    classify_errors: int


class IngestionHistoryResponse(BaseModel):
    next_run: Optional[datetime]
    recent_runs: List[IngestionRunOut]


@router.get("/ingestion/history", response_model=IngestionHistoryResponse)
async def get_ingestion_history(
    request: Request,
    _user: dict = Depends(clerk_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the last 10 ingestion runs and the next scheduled run time."""
    stmt = (
        select(IngestionRun)
        .order_by(IngestionRun.run_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    recent_runs = result.scalars().all()

    next_run: Optional[datetime] = None
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is not None:
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time

    return IngestionHistoryResponse(next_run=next_run, recent_runs=list(recent_runs))
