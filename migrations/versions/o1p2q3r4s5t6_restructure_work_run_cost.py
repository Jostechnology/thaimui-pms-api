"""restructure work run cost: drop per-machine table, add cost columns to machine, create per-run summary table

Revision ID: o1p2q3r4s5t6
Revises: m8n9o0p1q2r3
Create Date: 2026-04-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'o1p2q3r4s5t6'
down_revision = 'm8n9o0p1q2r3'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add cost rate + finalized cost columns directly on t_work_run_machine
    op.add_column('t_work_run_machine', sa.Column('depreciation_per_second', sa.Float(), nullable=False, server_default='0'))
    op.add_column('t_work_run_machine', sa.Column('maintenance_rate_per_second', sa.Float(), nullable=False, server_default='0'))
    op.add_column('t_work_run_machine', sa.Column('depreciation_cost', sa.Float(), nullable=True))
    op.add_column('t_work_run_machine', sa.Column('maintenance_cost', sa.Float(), nullable=True))

    # 2. Create per-work-run cost summary table
    op.create_table(
        't_work_run_cost',
        sa.Column('cost_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('material_cost', sa.Float(), nullable=True),
        sa.Column('depreciation_cost', sa.Float(), nullable=True),
        sa.Column('maintenance_cost', sa.Float(), nullable=True),
        sa.Column('labor_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cost_id'),
        sa.UniqueConstraint('work_run_id'),
    )

    # 3. Drop the old per-machine cost table
    op.drop_table('t_work_run_machine_cost')


def downgrade():
    op.drop_table('t_work_run_cost')

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

    op.drop_column('t_work_run_machine', 'maintenance_cost')
    op.drop_column('t_work_run_machine', 'depreciation_cost')
    op.drop_column('t_work_run_machine', 'maintenance_rate_per_second')
    op.drop_column('t_work_run_machine', 'depreciation_per_second')
