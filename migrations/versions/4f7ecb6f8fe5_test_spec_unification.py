"""TestSpec unification: t_test_spec + QCWorkOrder.test_spec_id.

Replaces the bare-boolean-by-proxy `QCWorkOrder.source_work_order_id`
(added in e0f1a2b3c4d5) with a proper `TestSpec` table that unifies the two
origins of a QC/test document: a manually created DIRECT spec, or a
COMPONENT_SECTION spec generated because one of the WorkOrder's
ItemComponent template sections declared a test. One spec per
(sales_item, item_component) — fixes concurrent-duplicate auto-QC and lets
two test-section components on the same sales item stay distinguishable.
See project_testspec_unification memory for the full trace (S4/S5/E8/E10/
job-2) that motivated this.

No backfill: dev period, old QC-source data (source_work_order_id) is
dropped outright rather than reconciled into TestSpec rows.

Revision ID: 4f7ecb6f8fe5
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = '4f7ecb6f8fe5'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        't_test_spec',
        sa.Column('test_spec_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('sales_item_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.Enum('DIRECT', 'COMPONENT_SECTION', name='testspecsourcetype'), nullable=False),
        sa.Column('item_component_id', sa.Integer(), nullable=True),
        sa.Column('item_component_version_id', sa.Integer(), nullable=True),
        sa.Column('section_keys', sa.JSON(), nullable=True),
        sa.Column('required_qty', sa.Double(), nullable=False),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('test_spec_id'),
        sa.ForeignKeyConstraint(['sales_item_id'], ['t_sales_items.sales_item_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.ForeignKeyConstraint(['item_component_id'], ['t_item_component.item_component_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['item_component_version_id'], ['t_item_component_version.version_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('sales_item_id', 'item_component_id', name='uq_test_spec_sales_item_component'),
    )
    op.create_index('ix_test_spec_sales_item', 't_test_spec', ['sales_item_id'])
    op.create_index('ix_test_spec_branch', 't_test_spec', ['branch_id'])

    op.add_column(
        't_qc_work_order',
        sa.Column('test_spec_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_qc_work_order_test_spec',
        't_qc_work_order', 't_test_spec',
        ['test_spec_id'], ['test_spec_id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_qc_work_order_test_spec',
        't_qc_work_order', ['test_spec_id'],
    )

    op.drop_index('ix_qc_work_order_source_work_order', table_name='t_qc_work_order')
    op.drop_constraint('fk_qc_work_order_source_work_order', 't_qc_work_order', type_='foreignkey')
    op.drop_column('t_qc_work_order', 'source_work_order_id')


def downgrade():
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

    op.drop_index('ix_qc_work_order_test_spec', table_name='t_qc_work_order')
    op.drop_constraint('fk_qc_work_order_test_spec', 't_qc_work_order', type_='foreignkey')
    op.drop_column('t_qc_work_order', 'test_spec_id')

    op.drop_index('ix_test_spec_branch', table_name='t_test_spec')
    op.drop_index('ix_test_spec_sales_item', table_name='t_test_spec')
    op.drop_table('t_test_spec')
    sa.Enum(name='testspecsourcetype').drop(op.get_bind(), checkfirst=True)
