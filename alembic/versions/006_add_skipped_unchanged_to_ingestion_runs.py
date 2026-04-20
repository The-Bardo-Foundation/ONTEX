"""add_skipped_unchanged_to_ingestion_runs

Revision ID: 006_add_skipped_unchanged
Revises: 005_drop_ai_matching_criteria
Create Date: 2026-04-20

Adds skipped_unchanged column to ingestion_runs. Tracks how many UPDATED trials
were silently skipped because only last_update_post_date changed, not content.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_add_skipped_unchanged"
down_revision: Union[str, None] = "005_drop_ai_matching_criteria"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "skipped_unchanged",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE ingestion_runs "
            "SET skipped_unchanged = 0 "
            "WHERE skipped_unchanged IS NULL"
        )
    )
    op.alter_column("ingestion_runs", "skipped_unchanged", nullable=False)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "skipped_unchanged")
