"""add qty_received_actual to picking_request_item

Revision ID: b1a2c3d4e5f6
Revises: adbcba965679
Create Date: 2026-05-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b1a2c3d4e5f6'
down_revision = 'adbcba965679'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        't_picking_request_item',
        sa.Column('qty_received_actual', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('t_picking_request_item', 'qty_received_actual')
