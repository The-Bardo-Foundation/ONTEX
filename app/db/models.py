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


class IrrelevantTrial(ClinicalTrialBase, Base):
    """Trials fetched but deemed irrelevant (stored for deduplication and auditing)."""

    __tablename__ = "irrelevant_trials"

    # Why it was marked irrelevant
    irrelevance_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)



