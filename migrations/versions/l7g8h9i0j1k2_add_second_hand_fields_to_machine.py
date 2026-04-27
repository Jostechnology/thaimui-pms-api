"""add is_second_hand and accumulated_hours to machine

Revision ID: l7g8h9i0j1k2
Revises: k6f7g8h9i0j1
Create Date: 2026-04-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'l7g8h9i0j1k2'
down_revision = ('n8o9p0q1r2s3', 'ced5dab8313d')
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('m_machine', sa.Column('is_second_hand', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('m_machine', sa.Column('accumulated_hours', sa.Float(), nullable=True, server_default='0.0'))


def downgrade():
    op.drop_column('m_machine', 'accumulated_hours')
    op.drop_column('m_machine', 'is_second_hand')
