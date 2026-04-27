"""add t_work_run_machine_cost table

Revision ID: m8n9o0p1q2r3
Revises: l7g8h9i0j1k2
Create Date: 2026-04-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'm8n9o0p1q2r3'
down_revision = 'l7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        't_work_run_machine_cost',
        sa.Column('cost_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('work_run_machine_id', sa.Integer(), nullable=False),
        sa.Column('depreciation_per_second', sa.Float(), nullable=False, server_default='0'),
        sa.Column('depreciation_cost', sa.Float(), nullable=True),
        sa.Column('maintenance_rate_per_second', sa.Float(), nullable=False, server_default='0'),
        sa.Column('maintenance_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.ForeignKeyConstraint(['work_run_machine_id'], ['t_work_run_machine.work_run_machine_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cost_id'),
        sa.UniqueConstraint('work_run_machine_id'),
    )


def downgrade():
    op.drop_table('t_work_run_machine_cost')
