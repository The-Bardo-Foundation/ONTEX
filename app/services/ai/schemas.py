from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    REJECT = "reject"


class ClassificationResult(BaseModel):
    label: ConfidenceLabel
    reason: str = Field(max_length=500)
