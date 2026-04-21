"""add counterparty_picking_request_item_id on t_picking_item_adjustment

Revision ID: m7n8o9p0q1r2
Revises: l6g7h8i9j0k1
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'm7n8o9p0q1r2'
down_revision = 'l6g7h8i9j0k1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        't_picking_item_adjustment',
        sa.Column('counterparty_picking_request_item_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_picking_item_adjustment_counterparty',
        source_table='t_picking_item_adjustment',
        referent_table='t_picking_request_item',
        local_cols=['counterparty_picking_request_item_id'],
        remote_cols=['picking_request_item_id'],
        ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint(
        'fk_picking_item_adjustment_counterparty',
        't_picking_item_adjustment',
        type_='foreignkey',
    )
    op.drop_column('t_picking_item_adjustment', 'counterparty_picking_request_item_id')
