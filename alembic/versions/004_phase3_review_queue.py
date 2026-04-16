"""phase3_review_queue

Revision ID: 004_phase3_review_queue
Revises: 003_add_tracking_columns
Create Date: 2026-04-16

Adds five columns to clinical_trials to support the Phase 3 admin review queue:

- ingestion_event: was this trial new or an update to a previously-approved trial?
- reviewer_notes: free-text note left by the reviewer on approve/reject
- rejected_at / rejected_by: parallel to approved_at/approved_by, set on rejection
- previous_official_snapshot: JSON snapshot of official_* fields captured at the
  moment an APPROVED trial is re-ingested as PENDING_REVIEW, used to render a
  diff view showing what changed since the last approved version
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_phase3_review_queue"
down_revision: Union[str, None] = "003_add_tracking_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # Create the enum type with a guard so re-running is idempotent
        op.execute(
            "DO $$ BEGIN IF NOT EXISTS "
            "(SELECT 1 FROM pg_type WHERE typname = 'ingestionevent') "
            "THEN CREATE TYPE ingestionevent AS ENUM ('NEW', 'UPDATED'); "
            "END IF; END $$;"
        )
        from sqlalchemy.dialects import postgresql
        ingestion_event_col = sa.Column(
            "ingestion_event",
            postgresql.ENUM("NEW", "UPDATED", name="ingestionevent", create_type=False),
            nullable=True,
        )
    else:
        # SQLite (and other backends) store enums as VARCHAR
        ingestion_event_col = sa.Column(
            "ingestion_event",
            sa.String(),
            nullable=True,
        )

    op.add_column("clinical_trials", ingestion_event_col)
    op.add_column("clinical_trials", sa.Column("reviewer_notes", sa.Text(), nullable=True))
    op.add_column("clinical_trials", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.add_column("clinical_trials", sa.Column("rejected_by", sa.String(), nullable=True))
    op.add_column("clinical_trials", sa.Column("previous_official_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("clinical_trials", "previous_official_snapshot")
    op.drop_column("clinical_trials", "rejected_by")
    op.drop_column("clinical_trials", "rejected_at")
    op.drop_column("clinical_trials", "reviewer_notes")
    op.drop_column("clinical_trials", "ingestion_event")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS ingestionevent")
