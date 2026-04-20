"""drop_ai_matching_criteria

Revision ID: 005_drop_ai_matching_criteria
Revises: 004_drop_relevance_tier
Create Date: 2026-04-20

Removes ai_matching_criteria from clinical_trials. The semantic tags it encoded
are no longer used — ai_relevance_label and ai_relevance_reason provide sufficient
signal for the editorial review workflow.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_drop_ai_matching_criteria"
down_revision: Union[str, None] = "004_drop_relevance_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("clinical_trials", "ai_matching_criteria")


def downgrade() -> None:
    op.add_column("clinical_trials", sa.Column("ai_matching_criteria", sa.Text(), nullable=True))
