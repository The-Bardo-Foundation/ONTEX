"""nct_id_as_primary_key

Revision ID: bab355f0ddc6
Revises: 001_initial_schema
Create Date: 2026-01-28 20:47:14.065769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bab355f0ddc6'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "irrelevant_trials" not in tables:
        op.create_table(
            'irrelevant_trials',
            sa.Column('irrelevance_reason', sa.String(), nullable=True),
            sa.Column('nct_id', sa.String(), nullable=False),
            sa.Column('brief_title', sa.String(), nullable=False),
            sa.Column('custom_brief_title', sa.String(), nullable=True),
            sa.Column('brief_summary', sa.Text(), nullable=True),
            sa.Column('custom_brief_summary', sa.Text(), nullable=True),
            sa.Column('overall_status', sa.String(), nullable=True),
            sa.Column('custom_overall_status', sa.String(), nullable=True),
            sa.Column('phase', sa.String(), nullable=True),
            sa.Column('custom_phase', sa.String(), nullable=True),
            sa.Column('study_type', sa.String(), nullable=True),
            sa.Column('custom_study_type', sa.String(), nullable=True),
            sa.Column('location_country', sa.String(), nullable=True),
            sa.Column('custom_location_country', sa.String(), nullable=True),
            sa.Column('location_city', sa.String(), nullable=True),
            sa.Column('custom_location_city', sa.String(), nullable=True),
            sa.Column('minimum_age', sa.String(), nullable=True),
            sa.Column('custom_minimum_age', sa.String(), nullable=True),
            sa.Column('maximum_age', sa.String(), nullable=True),
            sa.Column('custom_maximum_age', sa.String(), nullable=True),
            sa.Column('central_contact_name', sa.String(), nullable=True),
            sa.Column('custom_central_contact_name', sa.String(), nullable=True),
            sa.Column('central_contact_phone', sa.String(), nullable=True),
            sa.Column('custom_central_contact_phone', sa.String(), nullable=True),
            sa.Column('central_contact_email', sa.String(), nullable=True),
            sa.Column('custom_central_contact_email', sa.String(), nullable=True),
            sa.Column('eligibility_criteria', sa.Text(), nullable=True),
            sa.Column('custom_eligibility_criteria', sa.Text(), nullable=True),
            sa.Column('intervention_description', sa.Text(), nullable=True),
            sa.Column('custom_intervention_description', sa.Text(), nullable=True),
            sa.Column('key_information', sa.Text(), nullable=True),
            sa.Column('last_update_post_date', sa.String(), nullable=True),
            sa.Column('custom_last_update_post_date', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('nct_id')
        )

    clinical_cols = {c["name"] for c in inspector.get_columns("clinical_trials")}

    def add_if_missing(name: str, col: sa.Column) -> None:
        if name not in clinical_cols:
            op.add_column("clinical_trials", col)
            clinical_cols.add(name)

    add_if_missing('brief_title', sa.Column('brief_title', sa.String(), nullable=True))
    if "title" in clinical_cols:
        op.execute("UPDATE clinical_trials SET brief_title = title WHERE brief_title IS NULL")
    if dialect != "sqlite":
        op.alter_column('clinical_trials', 'brief_title', nullable=False)

    add_if_missing('custom_brief_title', sa.Column('custom_brief_title', sa.String(), nullable=True))
    add_if_missing('brief_summary', sa.Column('brief_summary', sa.Text(), nullable=True))
    add_if_missing('custom_brief_summary', sa.Column('custom_brief_summary', sa.Text(), nullable=True))
    add_if_missing('overall_status', sa.Column('overall_status', sa.String(), nullable=True))
    add_if_missing('custom_overall_status', sa.Column('custom_overall_status', sa.String(), nullable=True))
    add_if_missing('phase', sa.Column('phase', sa.String(), nullable=True))
    add_if_missing('custom_phase', sa.Column('custom_phase', sa.String(), nullable=True))
    add_if_missing('study_type', sa.Column('study_type', sa.String(), nullable=True))
    add_if_missing('custom_study_type', sa.Column('custom_study_type', sa.String(), nullable=True))
    add_if_missing('location_country', sa.Column('location_country', sa.String(), nullable=True))
    add_if_missing('custom_location_country', sa.Column('custom_location_country', sa.String(), nullable=True))
    add_if_missing('location_city', sa.Column('location_city', sa.String(), nullable=True))
    add_if_missing('custom_location_city', sa.Column('custom_location_city', sa.String(), nullable=True))
    add_if_missing('minimum_age', sa.Column('minimum_age', sa.String(), nullable=True))
    add_if_missing('custom_minimum_age', sa.Column('custom_minimum_age', sa.String(), nullable=True))
    add_if_missing('maximum_age', sa.Column('maximum_age', sa.String(), nullable=True))
    add_if_missing('custom_maximum_age', sa.Column('custom_maximum_age', sa.String(), nullable=True))
    add_if_missing('central_contact_name', sa.Column('central_contact_name', sa.String(), nullable=True))
    add_if_missing('custom_central_contact_name', sa.Column('custom_central_contact_name', sa.String(), nullable=True))
    add_if_missing('central_contact_phone', sa.Column('central_contact_phone', sa.String(), nullable=True))
    add_if_missing('custom_central_contact_phone', sa.Column('custom_central_contact_phone', sa.String(), nullable=True))
    add_if_missing('central_contact_email', sa.Column('central_contact_email', sa.String(), nullable=True))
    add_if_missing('custom_central_contact_email', sa.Column('custom_central_contact_email', sa.String(), nullable=True))
    add_if_missing('eligibility_criteria', sa.Column('eligibility_criteria', sa.Text(), nullable=True))
    add_if_missing('custom_eligibility_criteria', sa.Column('custom_eligibility_criteria', sa.Text(), nullable=True))
    add_if_missing('intervention_description', sa.Column('intervention_description', sa.Text(), nullable=True))
    add_if_missing('custom_intervention_description', sa.Column('custom_intervention_description', sa.Text(), nullable=True))
    add_if_missing('key_information', sa.Column('key_information', sa.Text(), nullable=True))
    add_if_missing('last_update_post_date', sa.Column('last_update_post_date', sa.String(), nullable=True))
    add_if_missing('custom_last_update_post_date', sa.Column('custom_last_update_post_date', sa.String(), nullable=True))

    if dialect != "sqlite":
        indexes = {idx["name"] for idx in inspector.get_indexes("clinical_trials")}
        if op.f("ix_clinical_trials_nct_id") in indexes:
            op.drop_index(op.f('ix_clinical_trials_nct_id'), table_name='clinical_trials')
        constraints = {c["name"] for c in inspector.get_unique_constraints("clinical_trials")}
        if op.f("uq_clinical_trials_nct_id") in constraints:
            op.drop_constraint(op.f('uq_clinical_trials_nct_id'), 'clinical_trials', type_='unique')
        if "title" in clinical_cols:
            op.drop_column('clinical_trials', 'title')
        if "id" in clinical_cols:
            op.drop_column('clinical_trials', 'id')
        if "last_updated" in clinical_cols:
            op.drop_column('clinical_trials', 'last_updated')
        if "custom_summary" in clinical_cols:
            op.drop_column('clinical_trials', 'custom_summary')
        if "official_summary" in clinical_cols:
            op.drop_column('clinical_trials', 'official_summary')


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clinical_trials', sa.Column('official_summary', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('clinical_trials', sa.Column('custom_summary', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('clinical_trials', sa.Column('last_updated', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('clinical_trials', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.add_column('clinical_trials', sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.create_unique_constraint(op.f('uq_clinical_trials_nct_id'), 'clinical_trials', ['nct_id'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('ix_clinical_trials_nct_id'), 'clinical_trials', ['nct_id'], unique=False)
    op.drop_column('clinical_trials', 'custom_last_update_post_date')
    op.drop_column('clinical_trials', 'last_update_post_date')
    op.drop_column('clinical_trials', 'key_information')
    op.drop_column('clinical_trials', 'custom_intervention_description')
    op.drop_column('clinical_trials', 'intervention_description')
    op.drop_column('clinical_trials', 'custom_eligibility_criteria')
    op.drop_column('clinical_trials', 'eligibility_criteria')
    op.drop_column('clinical_trials', 'custom_central_contact_email')
    op.drop_column('clinical_trials', 'central_contact_email')
    op.drop_column('clinical_trials', 'custom_central_contact_phone')
    op.drop_column('clinical_trials', 'central_contact_phone')
    op.drop_column('clinical_trials', 'custom_central_contact_name')
    op.drop_column('clinical_trials', 'central_contact_name')
    op.drop_column('clinical_trials', 'custom_maximum_age')
    op.drop_column('clinical_trials', 'maximum_age')
    op.drop_column('clinical_trials', 'custom_minimum_age')
    op.drop_column('clinical_trials', 'minimum_age')
    op.drop_column('clinical_trials', 'custom_location_city')
    op.drop_column('clinical_trials', 'location_city')
    op.drop_column('clinical_trials', 'custom_location_country')
    op.drop_column('clinical_trials', 'location_country')
    op.drop_column('clinical_trials', 'custom_study_type')
    op.drop_column('clinical_trials', 'study_type')
    op.drop_column('clinical_trials', 'custom_phase')
    op.drop_column('clinical_trials', 'phase')
    op.drop_column('clinical_trials', 'custom_overall_status')
    op.drop_column('clinical_trials', 'overall_status')
    op.drop_column('clinical_trials', 'custom_brief_summary')
    op.drop_column('clinical_trials', 'brief_summary')
    op.drop_column('clinical_trials', 'custom_brief_title')
    op.drop_column('clinical_trials', 'brief_title')
    op.drop_table('irrelevant_trials')
    # ### end Alembic commands ###
