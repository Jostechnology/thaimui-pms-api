"""employee/machine photo_key columns (MinIO object keys)

Revision ID: a6b7c8d9e0f1
Revises: f5e6a7b8c9d0
Create Date: 2026-07-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a6b7c8d9e0f1'
down_revision = 'f5e6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('m_employee', sa.Column('photo_key', sa.String(length=500), nullable=True))
    op.add_column('m_machine', sa.Column('photo_key', sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column('m_machine', 'photo_key')
    op.drop_column('m_employee', 'photo_key')
