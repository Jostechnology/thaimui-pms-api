"""Add t_test_result_break table and PAUSED status to TestSessionStatus enum

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-04-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 's5t6u7v8w9x0'
down_revision = 'r4s5t6u7v8w9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        't_test_result_break',
        sa.Column('break_id', sa.Integer(), nullable=False),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('break_start', sa.DateTime(), nullable=False),
        sa.Column('break_end', sa.DateTime(), nullable=True),
        sa.Column('break_type', sa.Enum('LUNCHBREAK', 'RESTBREAK', 'OTHER', name='breaktype'), nullable=False),
        sa.Column('remark', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('break_id'),
    )


def downgrade():
    op.drop_table('t_test_result_break')
