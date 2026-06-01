from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    REJECT = "reject"


class ClassificationResult(BaseModel):
    label: ConfidenceLabel
    reason: str = Field(max_length=500)


class AccuracyAdvice(BaseModel):
    """LLM analysis of where the classifier disagrees with reviewers."""

    summary: str = Field(default="", max_length=2000)
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
