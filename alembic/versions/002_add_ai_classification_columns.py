"""add_ai_classification_columns

Revision ID: 002_add_ai_classification_columns
Revises: bab355f0ddc6
Create Date: 2026-04-15

Adds four AI classification metadata columns to clinical_trials:
  - ai_relevance_confidence: float confidence score from the LLM (0.0–1.0)
  - ai_relevance_reason: LLM's explanation for the relevance decision
  - ai_relevance_tier: "primary" or "secondary" (from RelevanceTier enum)
  - ai_matching_criteria: JSON-encoded list of matching criteria tags

These columns are only on clinical_trials (not irrelevant_trials), because
irrelevant_trials already captures the reason via irrelevance_reason.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_ai_classification_columns"
down_revision: Union[str, None] = "bab355f0ddc6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # alembic_version.version_num was created as VARCHAR(32); our revision IDs exceed that
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(256)")
    op.add_column("clinical_trials", sa.Column("ai_relevance_confidence", sa.Float(), nullable=True))
    op.add_column("clinical_trials", sa.Column("ai_relevance_reason", sa.Text(), nullable=True))
    op.add_column("clinical_trials", sa.Column("ai_relevance_tier", sa.String(), nullable=True))
    op.add_column("clinical_trials", sa.Column("ai_matching_criteria", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("clinical_trials", "ai_matching_criteria")
    op.drop_column("clinical_trials", "ai_relevance_tier")
    op.drop_column("clinical_trials", "ai_relevance_reason")
    op.drop_column("clinical_trials", "ai_relevance_confidence")
