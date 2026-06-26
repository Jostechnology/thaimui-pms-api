"""test result enrichment: test_type, item test fields, check table

Revision ID: d3c4e5f6a7b8
Revises: c2b3d4e5f6a7
Create Date: 2026-06-25 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3c4e5f6a7b8'
down_revision = 'c2b3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # TestResult: controlled test type (nullable — do not mislabel historical rows)
    op.add_column(
        't_test_result',
        sa.Column(
            'test_type',
            sa.Enum('PROOF_LOAD', 'BREAKING', 'VISUAL', 'DIMENSIONAL', name='testtype'),
            nullable=True,
        ),
    )

    # TestResultItem: proof-load / breaking parameters + verdict reason
    op.add_column('t_test_result_item', sa.Column('required_load', sa.Float(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('hold_time_sec', sa.Integer(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('length_before', sa.Float(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('length_after', sa.Float(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('breaking_force', sa.Float(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('min_breaking_load', sa.Float(), nullable=True))
    op.add_column('t_test_result_item', sa.Column('fail_reason', sa.String(length=255), nullable=True))

    # Per-unit inspection checklist
    op.create_table(
        't_test_result_check',
        sa.Column('check_id', sa.Integer(), primary_key=True),
        sa.Column('test_result_item_id', sa.Integer(), nullable=False),
        sa.Column('check_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PASS', 'FAIL', 'NA', name='checkstatus'),
                  nullable=False, server_default='NA'),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['test_result_item_id'], ['t_test_result_item.test_result_item_id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
    )
    op.create_index('ix_t_test_result_check_branch_id', 't_test_result_check', ['branch_id'])
    op.create_index('ix_t_test_result_check_item', 't_test_result_check', ['test_result_item_id'])


def downgrade():
    op.drop_index('ix_t_test_result_check_item', table_name='t_test_result_check')
    op.drop_index('ix_t_test_result_check_branch_id', table_name='t_test_result_check')
    op.drop_table('t_test_result_check')

    op.drop_column('t_test_result_item', 'fail_reason')
    op.drop_column('t_test_result_item', 'min_breaking_load')
    op.drop_column('t_test_result_item', 'breaking_force')
    op.drop_column('t_test_result_item', 'length_after')
    op.drop_column('t_test_result_item', 'length_before')
    op.drop_column('t_test_result_item', 'hold_time_sec')
    op.drop_column('t_test_result_item', 'required_load')

    op.drop_column('t_test_result', 'test_type')

    bind = op.get_bind()
    sa.Enum(name='checkstatus').drop(bind, checkfirst=True)
    sa.Enum(name='testtype').drop(bind, checkfirst=True)
