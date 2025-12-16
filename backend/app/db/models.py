import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class TrialStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nct_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    official_summary: Mapped[str] = mapped_column(Text)
    custom_summary: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus), 
        default=TrialStatus.PENDING_REVIEW
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

