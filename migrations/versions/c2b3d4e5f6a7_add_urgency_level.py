"""add urgency_level to sales_order

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-05-25 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2b3d4e5f6a7'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        't_sales_order',
        sa.Column(
            'urgency_level',
            sa.Enum('LOW', 'NORMAL', 'HIGH', 'URGENT', name='urgencylevel'),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column('t_sales_order', 'urgency_level')
    bind = op.get_bind()
    sa.Enum(name='urgencylevel').drop(bind, checkfirst=True)
