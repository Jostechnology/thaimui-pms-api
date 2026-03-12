"""work_run usable_qty and updated transaction types

Revision ID: b3f1a2c4d5e6
Revises: 9a7ea6cd30c6
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'b3f1a2c4d5e6'
down_revision = '9a7ea6cd30c6'
branch_labels = None
depends_on = None


def upgrade():
    # Add usable_qty and completion_remark to t_work_run
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('usable_qty', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('completion_remark', sa.String(length=500), nullable=True))

    # Replace QUEUED_FOR_TEST / TESTED with TESTED_PASSED / TESTED_FAILED in t_sales_item_transaction
    with op.batch_alter_table('t_sales_item_transaction', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=mysql.ENUM('PRODUCED', 'QUEUED_FOR_TEST', 'TESTED'),
            type_=sa.Enum('PRODUCED', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('t_sales_item_transaction', schema=None) as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum('PRODUCED', 'TESTED_PASSED', 'TESTED_FAILED', name='salesitemtransactiontype'),
            type_=mysql.ENUM('PRODUCED', 'QUEUED_FOR_TEST', 'TESTED'),
            existing_nullable=False,
        )

    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.drop_column('completion_remark')
        batch_op.drop_column('usable_qty')
