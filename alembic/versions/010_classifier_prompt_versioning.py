"""classifier_prompt_versioning

Revision ID: 010_classifier_prompt_versioning
Revises: 009_accuracy_advice_runs
Create Date: 2026-06-04

Adds versioning for the classifier system prompt so the AI accuracy advice can
propose a rewritten prompt that an admin edits, backtests, and applies:

  - classifier_prompt_versions: one row per prompt version, exactly one active.
    Seeded with the current CLASSIFICATION_SYSTEM_PROMPT as the first active row.
  - backtest_runs: metrics from re-classifying decided trials with a candidate
    prompt, plus the baseline they are compared against.
  - accuracy_advice_runs gains proposed_prompt + prompt_version_id so each advice
    generation records the full rewritten prompt and the version it analysed.
"""

import sqlalchemy as sa
from alembic import op

from app.services.ai.prompts import CLASSIFICATION_SYSTEM_PROMPT

revision = "010_classifier_prompt_versioning"
down_revision = "009_accuracy_advice_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accuracy_advice_runs", sa.Column("proposed_prompt", sa.Text(), nullable=True)
    )
    op.add_column(
        "accuracy_advice_runs",
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
    )

    prompt_versions = op.create_table(
        "classifier_prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "advice_run_id",
            sa.Integer(),
            sa.ForeignKey("accuracy_advice_runs.id"),
            nullable=True,
        ),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ai_model", sa.String(), nullable=False),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("confident_error_rate", sa.Float(), nullable=True),
        sa.Column("unsure_rate", sa.Float(), nullable=True),
        sa.Column("false_negative_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("correct_auto_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("baseline_confident_error_rate", sa.Float(), nullable=True),
        sa.Column("baseline_unsure_rate", sa.Float(), nullable=True),
        sa.Column("baseline_false_negative_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("baseline_correct_auto_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # Seed the current hardcoded prompt as the first active version.
    op.bulk_insert(
        prompt_versions,
        [
            {
                "content": CLASSIFICATION_SYSTEM_PROMPT,
                "source": "seed",
                "note": "Initial prompt seeded from CLASSIFICATION_SYSTEM_PROMPT.",
                "is_active": True,
                "created_by": None,
                "advice_run_id": None,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("backtest_runs")
    op.drop_table("classifier_prompt_versions")
    op.drop_column("accuracy_advice_runs", "prompt_version_id")
    op.drop_column("accuracy_advice_runs", "proposed_prompt")
