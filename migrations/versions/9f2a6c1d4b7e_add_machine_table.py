"""add_machine_table

Revision ID: 9f2a6c1d4b7e
Revises: 579c996d6dcb
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f2a6c1d4b7e'
down_revision = '579c996d6dcb'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('m_machine'):
        return

    op.create_table(
        'm_machine',
        sa.Column('machine_id', sa.Integer(), nullable=False),
        sa.Column('machine_code', sa.String(length=50), nullable=False),
        sa.Column('machine_name', sa.String(length=255), nullable=False),
        sa.Column('machine_description', sa.String(length=500), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('purchase_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('RUNNING', 'DOWN', 'IDLE', 'OFFLINE', name='machinestatus'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint('machine_id'),
        sa.UniqueConstraint('machine_code')
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('m_machine'):
        op.drop_table('m_machine')
