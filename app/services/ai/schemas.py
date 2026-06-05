from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    REJECT = "reject"


class ClassificationResult(BaseModel):
    label: ConfidenceLabel
    reason: str = Field(max_length=500)


class PromptEdit(BaseModel):
    """A single surgical change to the classifier prompt (content only)."""

    action: Literal["replace", "insert_after", "insert_before", "append"]
    find: str | None = None
    content: str = Field(default="", max_length=8000)


class AccuracyAdvice(BaseModel):
    """LLM analysis of where the classifier disagrees with reviewers."""

    summary: str = Field(default="", max_length=2000)
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    # Surgical edits returned by the LLM; merged server-side into proposed_system_prompt.
    prompt_edits: list[PromptEdit] = Field(default_factory=list)
    # Active prompt + prompt_edits merged; unchanged sections stay verbatim.
    proposed_system_prompt: str = Field(default="")
