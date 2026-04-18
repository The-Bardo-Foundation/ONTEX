"""Initial schema with ClinicalTrial table

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-12-26

"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    # Create TrialStatus enum safely
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS "
        "(SELECT 1 FROM pg_type WHERE typname = 'trialstatus') "
        "THEN CREATE TYPE trialstatus AS ENUM "
        "('PENDING_REVIEW', 'APPROVED', 'REJECTED'); "
        "END IF; END $$;"
    )

    if "clinical_trials" not in tables:
        # Create clinical_trials table
        op.create_table(
            "clinical_trials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nct_id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("official_summary", sa.Text(), nullable=False),
            sa.Column("custom_summary", sa.Text(), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "PENDING_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    name="trialstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="PENDING_REVIEW",
            ),
            sa.Column(
                "last_updated",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes
        op.create_unique_constraint(
            "uq_clinical_trials_nct_id", "clinical_trials", ["nct_id"]
        )
        op.create_index("ix_clinical_trials_nct_id", "clinical_trials", ["nct_id"])


def downgrade() -> None:
    op.drop_index("ix_clinical_trials_nct_id", table_name="clinical_trials")
    op.drop_constraint("uq_clinical_trials_nct_id", "clinical_trials", type_="unique")
    op.drop_table("clinical_trials")

    op.execute("DROP TYPE IF EXISTS trialstatus")
