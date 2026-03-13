"""TestResult two-phase and IN_TESTING transaction type

Revision ID: c4d5e6f7a8b9
Revises: b3f1a2c4d5e6
Create Date: 2026-03-12

Changes:
- t_test_result: make work_run_id nullable, add claimed_qty, add session_status
- t_test_result: make overall_status nullable (set on finalize)
- t_sales_item_transaction: add IN_TESTING to enum
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'c4d5e6f7a8b9'
down_revision = 'b3f1a2c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('t_test_result', schema=None) as batch_op:
        # work_run_id: NOT NULL → NULL
        batch_op.alter_column(
            'work_run_id',
            existing_type=mysql.INTEGER(),
            nullable=True,
        )
        # Drop old CASCADE FK, re-create as SET NULL
        batch_op.drop_constraint('t_test_result_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_test_result_work_run',
            't_work_run', ['work_run_id'], ['work_run_id'],
            ondelete='SET NULL'
        )
        # overall_status: NOT NULL → NULL
        batch_op.alter_column(
            'overall_status',
            existing_type=mysql.ENUM('PASSED', 'FAILED'),
            nullable=True,
        )
        # New columns
        batch_op.add_column(sa.Column('claimed_qty', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column(
            'session_status',
            sa.Enum('INPROGRESS', 'COMPLETED', name='testsessionstatus'),
            nullable=False,
            server_default='INPROGRESS'
        ))

    # Add IN_TESTING to the SalesItemTransaction type enum
    with op.batch_alter_table('t_sales_item_transaction', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum('PRODUCED', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            type_=sa.Enum('PRODUCED', 'IN_TESTING', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('t_sales_item_transaction', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum('PRODUCED', 'IN_TESTING', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            type_=sa.Enum('PRODUCED', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            existing_nullable=False,
        )

    with op.batch_alter_table('t_test_result', schema=None) as batch_op:
        batch_op.drop_column('session_status')
        batch_op.drop_column('claimed_qty')
        batch_op.alter_column(
            'overall_status',
            existing_type=mysql.ENUM('PASSED', 'FAILED'),
            nullable=False,
        )
        batch_op.drop_constraint('fk_test_result_work_run', type_='foreignkey')
        batch_op.create_foreign_key(
            't_test_result_ibfk_2', 't_work_run', ['work_run_id'], ['work_run_id'],
            ondelete='CASCADE'
        )
        batch_op.alter_column(
            'work_run_id',
            existing_type=mysql.INTEGER(),
            nullable=False,
        )
