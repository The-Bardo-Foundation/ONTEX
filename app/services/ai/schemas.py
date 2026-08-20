from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    REJECT = "reject"


class ClassificationResult(BaseModel):
    label: ConfidenceLabel
    reason: str = Field(max_length=500)
    # True only when the AI call itself failed (LLM outage/error), as opposed to a
    # genuine verdict. Failed classifications are skipped by the ingestion pipeline
    # so the trial is refetched and re-evaluated on the next daily run.
    failed: bool = False
