"""keyword_management

Revision ID: 007_keyword_management
Revises: 006_add_skipped_unchanged
Create Date: 2026-04-20

Adds admin-managed search keywords, trial-keyword matches, and pruning metrics.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_keyword_management"
down_revision: Union[str, None] = "006_add_skipped_unchanged"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load_seed_terms() -> list[str]:
    try:
        from app.core.config import settings  # type: ignore

        configured = settings.SEARCH_TERMS or []
    except Exception:
        configured = ["osteosarcoma"]

    seen: set[str] = set()
    normalized: list[str] = []
    for term in configured:
        cleaned = (term or "").strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized or ["osteosarcoma"]


def upgrade() -> None:
    op.create_table(
        "search_keywords",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("term", name="uq_search_keywords_term"),
    )
    op.create_index("ix_search_keywords_term", "search_keywords", ["term"], unique=True)

    op.create_table(
        "trial_keyword_matches",
        sa.Column("nct_id", sa.String(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("matched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["keyword_id"], ["search_keywords.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("nct_id", "keyword_id", name="pk_trial_keyword_matches"),
    )
    op.create_index(
        "ix_trial_keyword_matches_nct_id", "trial_keyword_matches", ["nct_id"], unique=False
    )

    op.add_column(
        "ingestion_runs",
        sa.Column("pruned_trials", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )
    op.execute(
        sa.text(
            "UPDATE ingestion_runs "
            "SET pruned_trials = 0 "
            "WHERE pruned_trials IS NULL"
        )
    )
    op.alter_column("ingestion_runs", "pruned_trials", nullable=False)

    keywords_table = sa.table(
        "search_keywords",
        sa.column("term", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    rows = [{"term": term, "is_active": True} for term in _load_seed_terms()]
    if rows:
        op.bulk_insert(keywords_table, rows)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "pruned_trials")
    op.drop_index("ix_trial_keyword_matches_nct_id", table_name="trial_keyword_matches")
    op.drop_table("trial_keyword_matches")
    op.drop_index("ix_search_keywords_term", table_name="search_keywords")
    op.drop_table("search_keywords")
