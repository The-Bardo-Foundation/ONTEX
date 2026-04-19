from enum import Enum

from pydantic import BaseModel, Field


class RelevanceTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    IRRELEVANT = "irrelevant"


class ConfidenceLabel(str, Enum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    REJECT = "reject"


class ClassificationResult(BaseModel):
    label: ConfidenceLabel
    reason: str = Field(max_length=500)
    relevance_tier: RelevanceTier
    matching_criteria: list[str]
