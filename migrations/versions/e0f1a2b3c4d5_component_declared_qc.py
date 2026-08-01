"""Component test sections auto-declare a QCWorkOrder.

A WorkOrder component document can mark one of its sections as a TEST
SECTION — either at the template level (ComponentTemplate.sections JSON,
"is_test_section": true on a section object) or per-instance (an override on
the saved ComponentTemplateSectionData row). When any component of a
WorkOrder resolves at least one test section, the component document IS the
test spec, so the system auto-creates a QCWorkOrder instead of requiring QC
staff to make one by hand.

is_test_section on m_component_template_section_data is the per-instance
override. NULL means "inherit whatever the template section says" — it is
never backfilled, so every existing row keeps today's behaviour (fall back to
the template flag, which itself defaults to false for sections that predate
this feature).

source_work_order_id on t_qc_work_order marks a QCWorkOrder as
component-declared (auto-created) rather than manually created by QC staff —
non-null means "this QCWorkOrder exists because a component of that WorkOrder
declared a test section". SET NULL on WorkOrder delete: the QCWorkOrder (and
any TestResult already recorded against it) must outlive the WorkOrder that
originally declared it. No backfill needed — every existing QCWorkOrder was
manually created, so NULL is exactly the right default for all of them.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'm_component_template_section_data',
        sa.Column('is_test_section', sa.Boolean(), nullable=True),
    )

    op.add_column(
        't_qc_work_order',
        sa.Column('source_work_order_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_qc_work_order_source_work_order',
        't_qc_work_order', 't_work_order',
        ['source_work_order_id'], ['work_order_id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_qc_work_order_source_work_order',
        't_qc_work_order', ['source_work_order_id'],
    )


def downgrade():
    op.drop_index('ix_qc_work_order_source_work_order', table_name='t_qc_work_order')
    op.drop_constraint('fk_qc_work_order_source_work_order', 't_qc_work_order', type_='foreignkey')
    op.drop_column('t_qc_work_order', 'source_work_order_id')

    op.drop_column('m_component_template_section_data', 'is_test_section')
