"""accuracy_advice_runs

Revision ID: 009_accuracy_advice_runs
Revises: 008_add_clinical_trials_pkey
Create Date: 2026-06-01

Adds an append-only log of LLM accuracy-advice generations: a metric snapshot
plus the advice payload, so classifier prompt changes can be correlated with
drift in the confident-error and unsure rates over time.
"""

import sqlalchemy as sa
from alembic import op

revision = "009_accuracy_advice_runs"
down_revision = "008_add_clinical_trials_pkey"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accuracy_advice_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ai_model", sa.String(), nullable=False),
        sa.Column("confident_approved", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("confident_rejected", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("confident_error_rate", sa.Float(), nullable=True),
        sa.Column("unsure_approved", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsure_rejected", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsure_pending", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsure_approval_rate", sa.Float(), nullable=True),
        sa.Column("false_negative_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("examples_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("patterns", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("accuracy_advice_runs")
