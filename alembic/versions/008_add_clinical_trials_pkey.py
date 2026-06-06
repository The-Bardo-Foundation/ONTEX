"""add_clinical_trials_pkey

Revision ID: 008_add_clinical_trials_pkey
Revises: 007_expand_irrelevant_trials
Create Date: 2026-05-20

Fixes a latent schema bug: migration bab355f0ddc6 ("nct_id_as_primary_key")
dropped the old unique constraint and `id` column on clinical_trials but never
actually added the primary key on `nct_id`. The model declares it as PK so
SQLite (which builds from metadata) was unaffected, but Postgres (which builds
from migrations) ended up with no primary key, breaking any ON CONFLICT (nct_id)
upsert.
"""

from alembic import op


revision = "008_add_clinical_trials_pkey"
down_revision = "007_expand_irrelevant_trials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_primary_key("clinical_trials_pkey", "clinical_trials", ["nct_id"])


def downgrade() -> None:
    op.drop_constraint("clinical_trials_pkey", "clinical_trials", type_="primary")
