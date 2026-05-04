"""add t_test_result_assignment, t_test_result_machine, t_test_result_cost tables

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'q3r4s5t6u7v8'
down_revision = 'p2q3r4s5t6u7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        't_test_result_assignment',
        sa.Column('test_result_assignment_id', sa.Integer(), nullable=False),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('from_time', sa.DateTime(), nullable=False),
        sa.Column('to_time', sa.DateTime(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['m_employee.employee_id']),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_result_assignment_id'),
    )

    op.create_table(
        't_test_result_machine',
        sa.Column('test_result_machine_id', sa.Integer(), nullable=False),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('machine_id', sa.Integer(), nullable=False),
        sa.Column('from_time', sa.DateTime(), nullable=False),
        sa.Column('to_time', sa.DateTime(), nullable=True),
        sa.Column('allocated_maintenance_cost', sa.Float(), nullable=True),
        sa.Column('depreciation_per_second', sa.Float(), nullable=False),
        sa.Column('maintenance_rate_per_second', sa.Float(), nullable=False),
        sa.Column('depreciation_cost', sa.Float(), nullable=True),
        sa.Column('maintenance_cost', sa.Float(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['machine_id'], ['m_machine.machine_id']),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_result_machine_id'),
    )

    op.create_table(
        't_test_result_cost',
        sa.Column('cost_id', sa.Integer(), nullable=False),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('material_cost', sa.Float(), nullable=True),
        sa.Column('depreciation_cost', sa.Float(), nullable=True),
        sa.Column('maintenance_cost', sa.Float(), nullable=True),
        sa.Column('labor_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cost_id'),
        sa.UniqueConstraint('test_result_id'),
    )


def downgrade():
    op.drop_table('t_test_result_cost')
    op.drop_table('t_test_result_machine')
    op.drop_table('t_test_result_assignment')
