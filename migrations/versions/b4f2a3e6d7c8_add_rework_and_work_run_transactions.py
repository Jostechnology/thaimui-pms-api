"""add-rework-tables-and-work-run-transactions

Revision ID: b4f2a3e6d7c8
Revises: a1e380dfbadf
Create Date: 2026-03-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b4f2a3e6d7c8'
down_revision = 'a1e380dfbadf'
branch_labels = None
depends_on = None


def upgrade():
    # New table: rework source association (production defect rework)
    op.create_table(
        't_work_run_rework_source',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rework_work_run_id', sa.Integer(), nullable=False),
        sa.Column('source_work_run_id', sa.Integer(), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['rework_work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # New table: item-movement audit log for WorkRun
    op.create_table(
        't_work_run_transaction',
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('SENT_TO_TESTING', 'DEFECT_CONSUMED', name='workruntransactiontype'), nullable=False),
        sa.Column('related_document_code', sa.String(length=128), nullable=False),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('transaction_id'),
    )

    # New columns on t_work_run for test-failure rework linkage
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rework_source_test_result_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('qty_from_failed', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_work_run_rework_test_result',
            't_test_result',
            ['rework_source_test_result_id'],
            ['test_result_id'],
            ondelete='SET NULL',
        )


def downgrade():
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.drop_constraint('fk_work_run_rework_test_result', type_='foreignkey')
        batch_op.drop_column('qty_from_failed')
        batch_op.drop_column('rework_source_test_result_id')

    op.drop_table('t_work_run_transaction')
    op.drop_table('t_work_run_rework_source')
