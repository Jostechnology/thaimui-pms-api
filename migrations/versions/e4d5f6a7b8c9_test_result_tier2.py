"""test result tier 2: session photos, per-session spec, breaking load curve

Revision ID: e4d5f6a7b8c9
Revises: d3c4e5f6a7b8
Create Date: 2026-06-26 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4d5f6a7b8c9'
down_revision = 'd3c4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # B — breaking-test load curve stored whole as JSON on the item
    op.add_column('t_test_result_item', sa.Column('load_curve', sa.JSON(), nullable=True))

    # A — session evidence photos (object_key references MinIO)
    op.create_table(
        't_test_result_photo',
        sa.Column('photo_id', sa.Integer(), primary_key=True),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('object_key', sa.String(length=500), nullable=False),
        sa.Column('caption', sa.String(length=255), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
    )
    op.create_index('ix_t_test_result_photo_branch_id', 't_test_result_photo', ['branch_id'])
    op.create_index('ix_t_test_result_photo_tr', 't_test_result_photo', ['test_result_id'])

    # C — per-session product spec snapshot (1:1 with test result)
    op.create_table(
        't_test_result_spec',
        sa.Column('spec_id', sa.Integer(), primary_key=True),
        sa.Column('test_result_id', sa.Integer(), nullable=False),
        sa.Column('construction', sa.String(length=100), nullable=True),
        sa.Column('grade', sa.String(length=50), nullable=True),
        sa.Column('coating', sa.String(length=50), nullable=True),
        sa.Column('diameter', sa.Float(), nullable=True),
        sa.Column('nominal_length', sa.Float(), nullable=True),
        sa.Column('tensile_strength', sa.Float(), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('batch_no', sa.String(length=100), nullable=True),
        sa.Column('termination', sa.String(length=255), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['t_test_result.test_result_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.UniqueConstraint('test_result_id', name='uq_test_result_spec_tr'),
    )
    op.create_index('ix_t_test_result_spec_branch_id', 't_test_result_spec', ['branch_id'])


def downgrade():
    op.drop_index('ix_t_test_result_spec_branch_id', table_name='t_test_result_spec')
    op.drop_table('t_test_result_spec')

    op.drop_index('ix_t_test_result_photo_tr', table_name='t_test_result_photo')
    op.drop_index('ix_t_test_result_photo_branch_id', table_name='t_test_result_photo')
    op.drop_table('t_test_result_photo')

    op.drop_column('t_test_result_item', 'load_curve')
