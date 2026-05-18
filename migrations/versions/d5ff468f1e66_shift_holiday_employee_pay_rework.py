"""shift_holiday_employee_pay_rework

Revision ID: d5ff468f1e66
Revises: 854176b4b0ed
Create Date: 2026-05-14 15:37:29.913752

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = 'd5ff468f1e66'
down_revision = '854176b4b0ed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'm_holiday',
        sa.Column('holiday_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('holiday_date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('holiday_id'),
        sa.UniqueConstraint('holiday_date'),
    )

    op.create_table(
        'm_shift',
        sa.Column('shift_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='DEFAULT'),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('work_days', sa.String(length=40), nullable=False, server_default='MON,TUE,WED,THU,FRI'),
        sa.Column('ot_multiplier', sa.Float(), nullable=False, server_default='1.5'),
        sa.Column('weekend_multiplier', sa.Float(), nullable=False, server_default='2'),
        sa.Column('holiday_multiplier', sa.Float(), nullable=False, server_default='3'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('shift_id'),
    )

    op.create_table(
        'm_employee_shift',
        sa.Column('employee_shift_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('work_days', sa.String(length=40), nullable=False, server_default='MON,TUE,WED,THU,FRI'),
        sa.Column('created_by', sa.String(length=80), nullable=True),
        sa.Column('updated_by', sa.String(length=80), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['m_employee.employee_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('employee_shift_id'),
        sa.UniqueConstraint('employee_id'),
    )

    # Seed default shift row so labor cost service has config out of the box.
    op.execute(
        "INSERT INTO m_shift (name, start_time, end_time, work_days, ot_multiplier, weekend_multiplier, holiday_multiplier, is_default)"
        " VALUES ('DEFAULT', '08:00:00', '17:00:00', 'MON,TUE,WED,THU,FRI', 1.5, 2.0, 3.0, 1)"
    )

    with op.batch_alter_table('m_employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('base_salary', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('day_rate', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('ot_hourly_rate', sa.Float(), nullable=False, server_default='0'))

    # Backfill base_salary from legacy salary_base so existing employees keep their pay value.
    op.execute("UPDATE m_employee SET base_salary = salary_base")

    with op.batch_alter_table('m_employee', schema=None) as batch_op:
        batch_op.drop_column('salary_base')

    with op.batch_alter_table('t_employee_salary_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('old_base_salary', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('new_base_salary', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('old_day_rate', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('new_day_rate', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('old_ot_hourly_rate', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('new_ot_hourly_rate', sa.Float(), nullable=False, server_default='0'))

    op.execute("UPDATE t_employee_salary_history SET old_base_salary = old_salary, new_base_salary = new_salary")

    with op.batch_alter_table('t_employee_salary_history', schema=None) as batch_op:
        batch_op.drop_column('old_salary')
        batch_op.drop_column('new_salary')

    with op.batch_alter_table('t_work_run_cost', schema=None) as batch_op:
        batch_op.add_column(sa.Column('base_labor_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('day_labor_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('ot_labor_cost', sa.Float(), nullable=True))

    op.execute("UPDATE t_work_run_cost SET base_labor_cost = labor_cost")

    with op.batch_alter_table('t_work_run_cost', schema=None) as batch_op:
        batch_op.drop_column('labor_cost')

    with op.batch_alter_table('t_test_result_cost', schema=None) as batch_op:
        batch_op.add_column(sa.Column('base_labor_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('day_labor_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('ot_labor_cost', sa.Float(), nullable=True))

    op.execute("UPDATE t_test_result_cost SET base_labor_cost = labor_cost")

    with op.batch_alter_table('t_test_result_cost', schema=None) as batch_op:
        batch_op.drop_column('labor_cost')


def downgrade():
    with op.batch_alter_table('t_test_result_cost', schema=None) as batch_op:
        batch_op.add_column(sa.Column('labor_cost', mysql.FLOAT(), nullable=True))
    op.execute("UPDATE t_test_result_cost SET labor_cost = COALESCE(base_labor_cost,0) + COALESCE(day_labor_cost,0) + COALESCE(ot_labor_cost,0)")
    with op.batch_alter_table('t_test_result_cost', schema=None) as batch_op:
        batch_op.drop_column('ot_labor_cost')
        batch_op.drop_column('day_labor_cost')
        batch_op.drop_column('base_labor_cost')

    with op.batch_alter_table('t_work_run_cost', schema=None) as batch_op:
        batch_op.add_column(sa.Column('labor_cost', mysql.FLOAT(), nullable=True))
    op.execute("UPDATE t_work_run_cost SET labor_cost = COALESCE(base_labor_cost,0) + COALESCE(day_labor_cost,0) + COALESCE(ot_labor_cost,0)")
    with op.batch_alter_table('t_work_run_cost', schema=None) as batch_op:
        batch_op.drop_column('ot_labor_cost')
        batch_op.drop_column('day_labor_cost')
        batch_op.drop_column('base_labor_cost')

    with op.batch_alter_table('t_employee_salary_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('old_salary', mysql.FLOAT(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('new_salary', mysql.FLOAT(), nullable=False, server_default='0'))
    op.execute("UPDATE t_employee_salary_history SET old_salary = old_base_salary, new_salary = new_base_salary")
    with op.batch_alter_table('t_employee_salary_history', schema=None) as batch_op:
        batch_op.drop_column('new_ot_hourly_rate')
        batch_op.drop_column('old_ot_hourly_rate')
        batch_op.drop_column('new_day_rate')
        batch_op.drop_column('old_day_rate')
        batch_op.drop_column('new_base_salary')
        batch_op.drop_column('old_base_salary')

    with op.batch_alter_table('m_employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('salary_base', mysql.FLOAT(), nullable=False, server_default='0'))
    op.execute("UPDATE m_employee SET salary_base = base_salary")
    with op.batch_alter_table('m_employee', schema=None) as batch_op:
        batch_op.drop_column('ot_hourly_rate')
        batch_op.drop_column('day_rate')
        batch_op.drop_column('base_salary')

    op.drop_table('m_employee_shift')
    op.drop_table('m_shift')
    op.drop_table('m_holiday')
