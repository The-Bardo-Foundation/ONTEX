"""Classifier accuracy analysis.

Turns the human approve/reject decisions into insights about where the AI
classifier disagrees with reviewers. The product assumption is that `confident`
trials are trusted enough to auto-publish, so the analysis focuses on:

- a guardrail: the `confident` error rate (confident trials a human rejected)
  must stay near zero, otherwise auto-publishing confident trials is unsafe;
- the `unsure` bucket: how humans resolve unsure trials, and which segments are
  almost always approved or rejected (candidates to promote to confident /
  auto-reject), so the manual-review pile can shrink;
- false negatives: trials the AI rejected that a human later approved.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClinicalTrial, IrrelevantTrial, TrialStatus

EXAMPLE_LIMIT = 25
_UNKNOWN = "(unknown)"
_PATTERN_DIMENSIONS = ("phase", "study_type", "location_country")


@dataclass
class TrialExample:
    nct_id: str
    brief_title: str
    ai_relevance_label: Optional[str]
    ai_relevance_reason: Optional[str]
    reviewer_notes: Optional[str]
    human_decision: str  # "approved" | "rejected"


@dataclass
class PatternBucket:
    dimension: str  # "phase" | "study_type" | "location_country"
    value: str
    approved: int
    rejected: int


@dataclass
class AccuracyInsights:
    confident_approved: int
    confident_rejected: int
    confident_error_rate: Optional[float]
    unsure_approved: int
    unsure_rejected: int
    unsure_pending: int
    unsure_approval_rate: Optional[float]
    false_negative_count: int
    confident_false_positives: list[TrialExample]
    unsure_resolved: list[TrialExample]
    false_negatives: list[TrialExample]
    unsure_patterns: list[PatternBucket]


async def _scalar_count(db: AsyncSession, table, *filters) -> int:
    stmt = select(func.count()).select_from(table).where(*filters)
    return (await db.execute(stmt)).scalar() or 0


async def _grouped_counts(db: AsyncSession, column, *filters) -> dict[str, int]:
    stmt = select(column, func.count()).where(*filters).group_by(column)
    rows = (await db.execute(stmt)).all()
    return {(row[0] if row[0] is not None else _UNKNOWN): row[1] for row in rows}


def _approved_example(trial: ClinicalTrial) -> TrialExample:
    return TrialExample(
        nct_id=trial.nct_id,
        brief_title=trial.brief_title,
        ai_relevance_label=trial.ai_relevance_label,
        ai_relevance_reason=trial.ai_relevance_reason,
        reviewer_notes=trial.reviewer_notes,
        human_decision="approved",
    )


def _rejected_example(trial: IrrelevantTrial) -> TrialExample:
    return TrialExample(
        nct_id=trial.nct_id,
        brief_title=trial.brief_title,
        ai_relevance_label=trial.ai_relevance_label,
        ai_relevance_reason=trial.ai_relevance_reason,
        reviewer_notes=trial.reviewer_notes,
        human_decision="rejected",
    )


async def _approved_examples(db: AsyncSession, label: str) -> list[ClinicalTrial]:
    stmt = (
        select(ClinicalTrial)
        .where(
            ClinicalTrial.status == TrialStatus.APPROVED,
            ClinicalTrial.ai_relevance_label == label,
        )
        .limit(EXAMPLE_LIMIT)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _human_rejected_examples(db: AsyncSession, label: str) -> list[IrrelevantTrial]:
    stmt = (
        select(IrrelevantTrial)
        .where(
            IrrelevantTrial.rejected_by.isnot(None),
            IrrelevantTrial.ai_relevance_label == label,
        )
        .limit(EXAMPLE_LIMIT)
    )
    return list((await db.execute(stmt)).scalars().all())


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    return numerator / denominator if denominator else None


async def _unsure_patterns(db: AsyncSession) -> list[PatternBucket]:
    buckets: list[PatternBucket] = []
    for dimension in _PATTERN_DIMENSIONS:
        approved = await _grouped_counts(
            db,
            getattr(ClinicalTrial, dimension),
            ClinicalTrial.status == TrialStatus.APPROVED,
            ClinicalTrial.ai_relevance_label == "unsure",
        )
        rejected = await _grouped_counts(
            db,
            getattr(IrrelevantTrial, dimension),
            IrrelevantTrial.rejected_by.isnot(None),
            IrrelevantTrial.ai_relevance_label == "unsure",
        )
        for value in sorted(set(approved) | set(rejected)):
            buckets.append(
                PatternBucket(
                    dimension=dimension,
                    value=value,
                    approved=approved.get(value, 0),
                    rejected=rejected.get(value, 0),
                )
            )
    return buckets


async def compute_insights(db: AsyncSession) -> AccuracyInsights:
    confident_approved = await _scalar_count(
        db, ClinicalTrial,
        ClinicalTrial.status == TrialStatus.APPROVED,
        ClinicalTrial.ai_relevance_label == "confident",
    )
    confident_rejected = await _scalar_count(
        db, IrrelevantTrial,
        IrrelevantTrial.rejected_by.isnot(None),
        IrrelevantTrial.ai_relevance_label == "confident",
    )
    unsure_approved = await _scalar_count(
        db, ClinicalTrial,
        ClinicalTrial.status == TrialStatus.APPROVED,
        ClinicalTrial.ai_relevance_label == "unsure",
    )
    unsure_rejected = await _scalar_count(
        db, IrrelevantTrial,
        IrrelevantTrial.rejected_by.isnot(None),
        IrrelevantTrial.ai_relevance_label == "unsure",
    )
    unsure_pending = await _scalar_count(
        db, ClinicalTrial,
        ClinicalTrial.status == TrialStatus.PENDING_REVIEW,
        ClinicalTrial.ai_relevance_label == "unsure",
    )

    false_negative_count = await _scalar_count(
        db, ClinicalTrial,
        ClinicalTrial.status == TrialStatus.APPROVED,
        ClinicalTrial.ai_relevance_label == "reject",
    )

    fn_examples = await _approved_examples(db, "reject")
    confident_fp = await _human_rejected_examples(db, "confident")
    unsure_approved_rows = await _approved_examples(db, "unsure")
    unsure_rejected_rows = await _human_rejected_examples(db, "unsure")

    unsure_resolved = (
        [_approved_example(t) for t in unsure_approved_rows]
        + [_rejected_example(t) for t in unsure_rejected_rows]
    )[:EXAMPLE_LIMIT]

    return AccuracyInsights(
        confident_approved=confident_approved,
        confident_rejected=confident_rejected,
        confident_error_rate=_ratio(confident_rejected, confident_approved + confident_rejected),
        unsure_approved=unsure_approved,
        unsure_rejected=unsure_rejected,
        unsure_pending=unsure_pending,
        unsure_approval_rate=_ratio(unsure_approved, unsure_approved + unsure_rejected),
        false_negative_count=false_negative_count,
        confident_false_positives=[_rejected_example(t) for t in confident_fp],
        unsure_resolved=unsure_resolved,
        false_negatives=[_approved_example(t) for t in fn_examples],
        unsure_patterns=await _unsure_patterns(db),
    )
