"""reports persistence: m_report_definition + t_report_run (ADR-069 parity)

Revision ID: f5e6a7b8c9d0
Revises: e4d5f6a7b8c9
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f5e6a7b8c9d0'
down_revision = 'e4d5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'm_report_definition',
        sa.Column('code', sa.String(length=80), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=80), nullable=True),
        sa.Column('params_schema_json', sa.JSON(), nullable=False),
        sa.Column('supported_formats', sa.JSON(), nullable=False),
        sa.Column('definition_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
    )

    op.create_table(
        't_report_run',
        sa.Column('run_id', sa.String(length=36), primary_key=True),
        sa.Column('definition_code', sa.String(length=80), nullable=False),
        sa.Column('definition_version', sa.Integer(), nullable=False),
        sa.Column('params_json', sa.JSON(), nullable=False),
        sa.Column('requested_by', sa.String(length=80), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'running', 'completed', 'failed', name='reportrunstatus'),
            nullable=False,
        ),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('file_object_keys', sa.JSON(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('runtime_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['definition_code'], ['m_report_definition.code'], ondelete='RESTRICT',
        ),
    )
    op.create_index('ix_report_run_definition', 't_report_run', ['definition_code'])
    op.create_index('ix_report_run_requested', 't_report_run', ['requested_at'])
    op.create_index('ix_report_run_status', 't_report_run', ['status'])


def downgrade():
    op.drop_index('ix_report_run_status', table_name='t_report_run')
    op.drop_index('ix_report_run_requested', table_name='t_report_run')
    op.drop_index('ix_report_run_definition', table_name='t_report_run')
    op.drop_table('t_report_run')
    op.drop_table('m_report_definition')
