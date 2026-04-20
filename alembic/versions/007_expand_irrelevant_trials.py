"""expand_irrelevant_trials

Revision ID: 007_expand_irrelevant_trials
Revises: 006_add_skipped_unchanged
Create Date: 2026-04-20

Expands irrelevant_trials to store full rejection metadata for both AI and human
rejections. Replaces the narrow irrelevance_reason string with:
  - ai_relevance_label / ai_relevance_reason  (AI classification; mirrors clinical_trials)
  - rejected_at / rejected_by               (null rejected_by = AI; non-null = human)
  - reviewer_notes                           (human-provided note; null for AI rejections)
  - ingestion_event                          (NEW / UPDATED at time of rejection)

The old irrelevance_reason column is dropped; existing rows were AI-generated
reasons which are migrated into ai_relevance_reason.
"""

from alembic import op
import sqlalchemy as sa

revision = '007_expand_irrelevant_trials'
down_revision = '006_add_skipped_unchanged'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migrate old irrelevance_reason data into the new ai_relevance_reason column,
    # then drop the old column.
    op.add_column('irrelevant_trials', sa.Column('ai_relevance_reason', sa.Text(), nullable=True))
    op.execute("UPDATE irrelevant_trials SET ai_relevance_reason = irrelevance_reason")
    op.drop_column('irrelevant_trials', 'irrelevance_reason')

    op.add_column('irrelevant_trials', sa.Column('ai_relevance_label', sa.String(), nullable=True))
    op.add_column('irrelevant_trials', sa.Column('rejected_at', sa.DateTime(), nullable=True))
    op.add_column('irrelevant_trials', sa.Column('rejected_by', sa.String(), nullable=True))
    op.add_column('irrelevant_trials', sa.Column('reviewer_notes', sa.Text(), nullable=True))
    # ingestionevent enum already exists in the DB from clinical_trials; create_type=False
    op.add_column(
        'irrelevant_trials',
        sa.Column(
            'ingestion_event',
            sa.Enum('NEW', 'UPDATED', name='ingestionevent', create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.add_column('irrelevant_trials', sa.Column('irrelevance_reason', sa.String(), nullable=True))
    op.execute("UPDATE irrelevant_trials SET irrelevance_reason = ai_relevance_reason")
    op.drop_column('irrelevant_trials', 'ai_relevance_reason')
    op.drop_column('irrelevant_trials', 'ai_relevance_label')
    op.drop_column('irrelevant_trials', 'rejected_at')
    op.drop_column('irrelevant_trials', 'rejected_by')
    op.drop_column('irrelevant_trials', 'reviewer_notes')
    op.drop_column('irrelevant_trials', 'ingestion_event')
