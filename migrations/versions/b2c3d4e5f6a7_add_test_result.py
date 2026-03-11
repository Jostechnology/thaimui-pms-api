"""add_test_result

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-07 20:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add quantity to t_qc_work_order
    with op.batch_alter_table('t_qc_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))

    # Create t_test_result
    op.create_table(
        't_test_result',
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('qc_work_order_id', sa.Integer(), nullable=False),
        sa.Column('test_date', sa.DateTime(), nullable=True),
        sa.Column('tested_by', sa.String(length=100), nullable=True),
        sa.Column('test_method', sa.String(length=255), nullable=True),
        sa.Column('standard_reference', sa.String(length=255), nullable=True),
        sa.Column('overall_status', sa.Enum('PASSED', 'FAILED', name='testresultstatus'), nullable=False),
        sa.Column('remark', sa.String(length=500), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(['qc_work_order_id'], ['t_qc_work_order.qc_work_order_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_result_id'),
    )

    # Create t_test_result_item (unit_number instead of qc_item_id — 1 row per tested unit)
    op.create_table(
        't_test_result_item',
        sa.Column('test_result_item_id', sa.Integer(), nullable=False),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('unit_number', sa.Integer(), nullable=False),
        sa.Column('serial_no', sa.String(length=200), nullable=True),
        sa.Column('wll_measured', sa.Float(), nullable=True),
        sa.Column('load_test_value', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('result', sa.Enum('PASSED', 'FAILED', name='testresultstatus'), nullable=False),
        sa.Column('remark', sa.String(length=500), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_result_item_id'),
    )

    # Add test_result_item_id FK to t_qc_check_item
    with op.batch_alter_table('t_qc_check_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('test_result_item_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_qc_check_item_test_result_item', 't_test_result_item', ['test_result_item_id'], ['test_result_item_id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('t_qc_check_item', schema=None) as batch_op:
        batch_op.drop_constraint('fk_qc_check_item_test_result_item', type_='foreignkey')
        batch_op.drop_column('test_result_item_id')

    op.drop_table('t_test_result_item')
    op.drop_table('t_test_result')

    with op.batch_alter_table('t_qc_work_order', schema=None) as batch_op:
        batch_op.drop_column('quantity')
