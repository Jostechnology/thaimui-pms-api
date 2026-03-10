"""add sales item transaction

Revision ID: a1c2e3f4b5d6
Revises: 3c4afddf9fbb
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1c2e3f4b5d6'
down_revision = '3c4afddf9fbb'
branch_labels = None
depends_on = None


def upgrade():
    # Add quantity column to work order
    op.add_column('t_work_order', sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))

    # Create sales item transaction table
    op.create_table(
        't_sales_item_transaction',
        sa.Column('transaction_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sales_item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('PRODUCED', 'QUEUED_FOR_TEST', 'TESTED', name='salesitemtransactiontype'), nullable=False),
        sa.Column('related_document_code', sa.String(length=128), nullable=False),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sales_item_id'], ['t_sales_items.sales_item_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('transaction_id'),
    )


def downgrade():
    op.drop_table('t_sales_item_transaction')
    op.drop_column('t_work_order', 'quantity')
