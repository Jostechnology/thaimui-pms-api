"""add REALLOCATE reason and is_reallocation on t_picking_request

Revision ID: l6g7h8i9j0k1
Revises: d8a83ec85856
Create Date: 2026-04-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'l6g7h8i9j0k1'
down_revision = 'd8a83ec85856'
branch_labels = None
depends_on = None


OLD_REASONS = ('MISCOUNT', 'SPILLAGE', 'CORRECTION', 'OTHER')
NEW_REASONS = ('MISCOUNT', 'SPILLAGE', 'CORRECTION', 'REALLOCATE', 'OTHER')


def upgrade():
    op.add_column(
        't_picking_request',
        sa.Column('is_reallocation', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.alter_column(
        't_picking_item_adjustment',
        'reason',
        existing_type=sa.Enum(*OLD_REASONS, name='pickingitemadjustmentreason'),
        type_=sa.Enum(*NEW_REASONS, name='pickingitemadjustmentreason'),
        existing_nullable=False,
    )


def downgrade():
    op.execute(
        "UPDATE t_picking_item_adjustment SET reason = 'OTHER' WHERE reason = 'REALLOCATE'"
    )
    op.alter_column(
        't_picking_item_adjustment',
        'reason',
        existing_type=sa.Enum(*NEW_REASONS, name='pickingitemadjustmentreason'),
        type_=sa.Enum(*OLD_REASONS, name='pickingitemadjustmentreason'),
        existing_nullable=False,
    )

    op.drop_column('t_picking_request', 'is_reallocation')
