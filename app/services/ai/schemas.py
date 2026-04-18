from enum import Enum

from pydantic import BaseModel, Field


class RelevanceTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    IRRELEVANT = "irrelevant"


class ClassificationResult(BaseModel):
    is_relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=500)
    relevance_tier: RelevanceTier
    matching_criteria: list[str]
