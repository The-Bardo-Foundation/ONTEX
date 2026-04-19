"""rename_confidence_to_label

Revision ID: 003_rename_confidence_to_label
Revises: 004_phase3_review_queue
Create Date: 2026-04-19

Replaces ai_relevance_confidence (float 0-1) with ai_relevance_label (string).
The new label is one of: "confident", "unsure", "reject".

Migration of existing data:
  confidence >= 0.7  → "confident"
  confidence <  0.7  → "unsure"
  NULL               → NULL
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_rename_confidence_to_label"
down_revision: Union[str, None] = "004_phase3_review_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinical_trials", sa.Column("ai_relevance_label", sa.String(), nullable=True))
    op.execute("""
        UPDATE clinical_trials
        SET ai_relevance_label = CASE
            WHEN ai_relevance_confidence IS NULL THEN NULL
            WHEN ai_relevance_confidence >= 0.7 THEN 'confident'
            ELSE 'unsure'
        END
    """)
    op.drop_column("clinical_trials", "ai_relevance_confidence")


def downgrade() -> None:
    op.add_column("clinical_trials", sa.Column("ai_relevance_confidence", sa.Float(), nullable=True))
    op.execute("""
        UPDATE clinical_trials
        SET ai_relevance_confidence = CASE
            WHEN ai_relevance_label = 'confident' THEN 1.0
            WHEN ai_relevance_label = 'unsure' THEN 0.5
            WHEN ai_relevance_label = 'reject' THEN 0.0
            ELSE NULL
        END
    """)
    op.drop_column("clinical_trials", "ai_relevance_label")
