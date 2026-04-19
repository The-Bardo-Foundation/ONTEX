"""drop_relevance_tier

Revision ID: 004_drop_relevance_tier
Revises: 003_rename_confidence_to_label
Create Date: 2026-04-19

Removes ai_relevance_tier from clinical_trials. The primary/secondary distinction
it encoded is now redundant — the matching_criteria tags carry the same signal
more precisely (e.g. osteosarcoma_in_conditions vs broad_sarcoma_trial).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_drop_relevance_tier"
down_revision: Union[str, None] = "003_rename_confidence_to_label"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("clinical_trials", "ai_relevance_tier")


def downgrade() -> None:
    op.add_column("clinical_trials", sa.Column("ai_relevance_tier", sa.String(), nullable=True))
