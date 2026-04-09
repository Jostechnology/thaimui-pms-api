"""flatten_work_phase_onto_work_run

Revision ID: a1b2c3d4e5f7
Revises: 58f163475f9d
Create Date: 2026-04-09

Drops t_work_phase, t_work_phase_break, t_work_assignment.
Adds t_work_run_assignment, t_work_run_machine, t_work_run_break.
Adds start_date, end_date to t_work_run and expands its status enum.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f7'
down_revision = '58f163475f9d'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop FK from t_work_run → t_work_phase (current_phase_id) first,
    #    so we can then drop t_work_phase without MySQL complaining.
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.drop_constraint('fk_work_run_current_phase_id', type_='foreignkey')
        batch_op.drop_column('current_phase_id')

    # 2. Drop old phase tables. t_work_phase_break and t_work_assignment CASCADE
    #    via their own FKs to t_work_phase, so drop children first.
    op.drop_table('t_work_assignment')
    op.drop_table('t_work_phase_break')
    op.drop_table('t_work_phase')

    # 3. Expand WorkRun status enum and add new columns
    op.execute(
        "ALTER TABLE t_work_run MODIFY COLUMN status "
        "ENUM('PENDING','INPROGRESS','PAUSED','COMPLETED') NOT NULL DEFAULT 'PENDING'"
    )

    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('end_date', sa.DateTime(), nullable=True))

    # 4. Create t_work_run_assignment
    op.create_table(
        't_work_run_assignment',
        sa.Column('work_run_assignment_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('from_time', sa.DateTime(), nullable=False),
        sa.Column('to_time', sa.DateTime(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['m_employee.employee_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('work_run_assignment_id'),
    )
    op.create_index('ix_work_run_assignment_branch_id', 't_work_run_assignment', ['branch_id'])

    # 5. Create t_work_run_machine
    op.create_table(
        't_work_run_machine',
        sa.Column('work_run_machine_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('machine_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('from_time', sa.DateTime(), nullable=False),
        sa.Column('to_time', sa.DateTime(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['machine_id'], ['m_machine.machine_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('work_run_machine_id'),
    )
    op.create_index('ix_work_run_machine_branch_id', 't_work_run_machine', ['branch_id'])

    # 6. Create t_work_run_break
    op.create_table(
        't_work_run_break',
        sa.Column('break_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('break_start', sa.DateTime(), nullable=False),
        sa.Column('break_end', sa.DateTime(), nullable=True),
        sa.Column('break_type', sa.Enum('LUNCHBREAK', 'RESTBREAK', 'OTHER'), nullable=False),
        sa.Column('remark', sa.String(255), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('break_id'),
    )
    op.create_index('ix_work_run_break_branch_id', 't_work_run_break', ['branch_id'])


def downgrade():
    op.drop_index('ix_work_run_break_branch_id', 't_work_run_break')
    op.drop_table('t_work_run_break')
    op.drop_index('ix_work_run_machine_branch_id', 't_work_run_machine')
    op.drop_table('t_work_run_machine')
    op.drop_index('ix_work_run_assignment_branch_id', 't_work_run_assignment')
    op.drop_table('t_work_run_assignment')

    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.drop_column('end_date')
        batch_op.drop_column('start_date')

    op.execute(
        "ALTER TABLE t_work_run MODIFY COLUMN status "
        "ENUM('INPROGRESS','COMPLETED') NOT NULL DEFAULT 'INPROGRESS'"
    )

    op.create_table(
        't_work_phase',
        sa.Column('work_phase_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('phase_name', sa.String(100), nullable=False),
        sa.Column('phase_status', sa.Enum('PENDING', 'INPROGRESS', 'PAUSED', 'COMPLETED'), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_run_id'], ['t_work_run.work_run_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('work_phase_id'),
    )
    op.create_table(
        't_work_phase_break',
        sa.Column('break_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_phase_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('break_start', sa.DateTime(), nullable=False),
        sa.Column('break_end', sa.DateTime(), nullable=True),
        sa.Column('break_type', sa.Enum('LUNCHBREAK', 'RESTBREAK', 'OTHER'), nullable=False),
        sa.Column('Remark', sa.String(255), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_phase_id'], ['t_work_phase.work_phase_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('break_id'),
    )
    op.create_table(
        't_work_assignment',
        sa.Column('work_assignment_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('work_phase_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(80), nullable=True),
        sa.Column('updated_by', sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(['work_phase_id'], ['t_work_phase.work_phase_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['m_employee.employee_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['m_branch.branch_id']),
        sa.PrimaryKeyConstraint('work_assignment_id'),
    )

    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_phase_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_work_run_current_phase_id',
            't_work_phase', ['current_phase_id'], ['work_phase_id']
        )
