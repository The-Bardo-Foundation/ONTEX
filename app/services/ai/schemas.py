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
    # True only when the AI call itself failed (LLM outage/error), as opposed to a
    # genuine verdict. Failed classifications are skipped by the ingestion pipeline
    # so the trial is refetched and re-evaluated on the next daily run.
    failed: bool = False


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
