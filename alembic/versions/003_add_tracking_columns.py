"""add_tracking_columns

Revision ID: 003_add_tracking_columns
Revises: 002_add_ai_classification_columns
Create Date: 2026-04-15

Adds two sets of changes:

1. Approval-tracking columns on clinical_trials (Phase 1.5):
   - approved_at / approved_by: set by the /approve endpoint
   - previous_approved_at / previous_approved_by: preserved when an APPROVED
     trial is reset to PENDING_REVIEW by re-ingestion, so reviewers can see
     who last signed off and when

2. ingestion_runs table (Phase 1.6):
   One row per pipeline execution — queryable audit trail with counts of
   new/updated/re-evaluated trials, errors, and totals.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_tracking_columns"
down_revision: Union[str, None] = "002_add_ai_classification_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Approval-tracking columns on clinical_trials ──────────────────────────
    op.add_column("clinical_trials", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("clinical_trials", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column("clinical_trials", sa.Column("previous_approved_at", sa.DateTime(), nullable=True))
    op.add_column("clinical_trials", sa.Column("previous_approved_by", sa.String(), nullable=True))

    # ── Ingestion run audit table ─────────────────────────────────────────────
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=False),
        sa.Column("search_terms", sa.Text(), nullable=True),
        sa.Column("candidates_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reeval_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevant_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("irrelevant_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetch_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("classify_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")

    op.drop_column("clinical_trials", "previous_approved_by")
    op.drop_column("clinical_trials", "previous_approved_at")
    op.drop_column("clinical_trials", "approved_by")
    op.drop_column("clinical_trials", "approved_at")
