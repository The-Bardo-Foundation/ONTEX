import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TrialStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class IngestionEvent(str, enum.Enum):
    NEW = "NEW"
    UPDATED = "UPDATED"


class ClinicalTrialBase:
    """Mixin with all clinical trial fields shared between relevant and irrelevant trials."""

    nct_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Title
    brief_title: Mapped[str] = mapped_column(String)
    custom_brief_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Summary
    brief_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_brief_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Trial Status & Phase
    overall_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_overall_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    study_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_study_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Location
    location_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_location_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location_city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_location_city: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Age Requirements
    minimum_age: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_minimum_age: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    maximum_age: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_maximum_age: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Contact Information
    central_contact_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_central_contact_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    central_contact_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_central_contact_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    central_contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_central_contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Eligibility & Intervention
    eligibility_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_eligibility_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intervention_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_intervention_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Custom-only fields (no original from ClinicalTrials.gov)
    key_information: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dates
    last_update_post_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_last_update_post_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)



class ClinicalTrial(ClinicalTrialBase, Base):
    """Relevant clinical trials for review and publication."""

    __tablename__ = "clinical_trials"

    # Review workflow status
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus), default=TrialStatus.PENDING_REVIEW
    )

    # AI classification metadata (set during ingestion, not on IrrelevantTrial)
    ai_relevance_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_relevance_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval tracking — set by PATCH /approve endpoint, preserved across re-ingestions
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Previous approval — captured when an APPROVED trial is reset to PENDING_REVIEW
    previous_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    previous_approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Rejection tracking — set by PATCH /reject endpoint
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Reviewer notes — free-text note left on approve or reject
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ingestion event — was this trial new or an update to a previously-approved one?
    ingestion_event: Mapped[Optional[IngestionEvent]] = mapped_column(
        Enum(IngestionEvent), nullable=True
    )

    # Snapshot of official_* fields at the moment an APPROVED trial was re-ingested.
    # Stored as a JSON string; decoded at the application layer for the diff view.
    previous_official_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class IrrelevantTrial(ClinicalTrialBase, Base):
    """Trials rejected by AI or human reviewer (stored for deduplication and auditing)."""

    __tablename__ = "irrelevant_trials"

    # AI classification — set by ingestion pipeline; null for human-only rejections
    ai_relevance_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_relevance_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rejection tracking — null rejected_by means AI rejected; non-null means human
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Free-text note from the human reviewer (not set for AI rejections)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ingestion event at time of rejection
    ingestion_event: Mapped[Optional[IngestionEvent]] = mapped_column(
        Enum(IngestionEvent, create_type=False), nullable=True
    )


class IngestionRun(Base):
    """One record per ingestion pipeline execution — queryable audit trail."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime)
    search_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-encoded list
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    new_trials: Mapped[int] = mapped_column(Integer, default=0)
    updated_trials: Mapped[int] = mapped_column(Integer, default=0)
    reeval_trials: Mapped[int] = mapped_column(Integer, default=0)
    relevant_processed: Mapped[int] = mapped_column(Integer, default=0)
    irrelevant_processed: Mapped[int] = mapped_column(Integer, default=0)
    fetch_errors: Mapped[int] = mapped_column(Integer, default=0)
    classify_errors: Mapped[int] = mapped_column(Integer, default=0)
    skipped_unchanged: Mapped[int] = mapped_column(Integer, default=0)

