"""reservation + actuals model: required items, qty_allocated/consumed, QCItem enrichment

Revision ID: k6f7g8h9i0j1
Revises: j5e6f7g8h9i0
Create Date: 2026-04-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = 'k6f7g8h9i0j1'
down_revision = 'j5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade():
    # --- Add PENDING to testsessionstatus enum ---
    op.execute("ALTER TABLE t_test_result MODIFY COLUMN session_status ENUM('PENDING','INPROGRESS','COMPLETED') NOT NULL")

    # --- Enrich QCItem ---
    op.add_column('t_qc_item',
        sa.Column('material_list_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_qc_item_material_list',
        't_qc_item', 't_material_list',
        ['material_list_id'], ['material_list_id'],
        ondelete='SET NULL'
    )
    op.add_column('t_qc_item',
        sa.Column('required_qty', sa.Integer(), nullable=True)
    )

    # --- t_test_result_required_item (new) ---
    op.create_table(
        't_test_result_required_item',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('test_result_id', sa.Integer(),
                  sa.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False),
        sa.Column('qc_item_id', sa.Integer(),
                  sa.ForeignKey('t_qc_item.qc_item_id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_list_id', sa.Integer(),
                  sa.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_code', sa.String(100), nullable=False),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('required_qty', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('qty_consumed_actual', sa.Integer(), nullable=True),
        sa.Column('branch_id', sa.Integer(),
                  sa.ForeignKey('m_branch.branch_id'), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
    )

    # --- t_test_result_picking_item: rename qty_consumed → qty_allocated, add new qty_consumed + FK ---
    op.alter_column('t_test_result_picking_item', 'qty_consumed',
                    new_column_name='qty_allocated', existing_type=sa.Integer(), nullable=False)
    op.add_column('t_test_result_picking_item',
        sa.Column('qty_consumed', sa.Integer(), nullable=True)
    )
    op.add_column('t_test_result_picking_item',
        sa.Column('test_result_required_item_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_trpi_required_item',
        't_test_result_picking_item', 't_test_result_required_item',
        ['test_result_required_item_id'], ['id'],
        ondelete='SET NULL'
    )

    # --- Backfill: COMPLETED test results → qty_consumed = qty_allocated ---
    op.execute("""
        UPDATE t_test_result_picking_item trpi
        JOIN t_test_result tr ON tr.test_result_id = trpi.test_result_id
        SET trpi.qty_consumed = trpi.qty_allocated
        WHERE tr.session_status = 'COMPLETED'
    """)

    # --- t_work_run_required_item: add qty_consumed_actual ---
    op.add_column('t_work_run_required_item',
        sa.Column('qty_consumed_actual', sa.Integer(), nullable=True)
    )

    # --- t_work_run_picking_item: rename qty_consumed → qty_allocated, add new qty_consumed + FK ---
    op.alter_column('t_work_run_picking_item', 'qty_consumed',
                    new_column_name='qty_allocated', existing_type=sa.Integer(), nullable=False)
    op.add_column('t_work_run_picking_item',
        sa.Column('qty_consumed', sa.Integer(), nullable=True)
    )
    op.add_column('t_work_run_picking_item',
        sa.Column('work_run_required_item_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_wrpi_required_item',
        't_work_run_picking_item', 't_work_run_required_item',
        ['work_run_required_item_id'], ['id'],
        ondelete='SET NULL'
    )

    # --- Backfill: COMPLETED work runs → qty_consumed = qty_allocated ---
    op.execute("""
        UPDATE t_work_run_picking_item wrpi
        JOIN t_work_run wr ON wr.work_run_id = wrpi.work_run_id
        SET wrpi.qty_consumed = wrpi.qty_allocated
        WHERE wr.status = 'COMPLETED'
    """)


def downgrade():
    # WorkRunPickingItem
    op.drop_constraint('fk_wrpi_required_item', 't_work_run_picking_item', type_='foreignkey')
    op.drop_column('t_work_run_picking_item', 'work_run_required_item_id')
    op.drop_column('t_work_run_picking_item', 'qty_consumed')
    op.alter_column('t_work_run_picking_item', 'qty_allocated',
                    new_column_name='qty_consumed', existing_type=sa.Integer(), nullable=False)

    # WorkRunRequiredItem
    op.drop_column('t_work_run_required_item', 'qty_consumed_actual')

    # TestResultPickingItem
    op.drop_constraint('fk_trpi_required_item', 't_test_result_picking_item', type_='foreignkey')
    op.drop_column('t_test_result_picking_item', 'test_result_required_item_id')
    op.drop_column('t_test_result_picking_item', 'qty_consumed')
    op.alter_column('t_test_result_picking_item', 'qty_allocated',
                    new_column_name='qty_consumed', existing_type=sa.Integer(), nullable=False)

    # TestResultRequiredItem table
    op.drop_table('t_test_result_required_item')

    # QCItem
    op.drop_constraint('fk_qc_item_material_list', 't_qc_item', type_='foreignkey')
    op.drop_column('t_qc_item', 'required_qty')
    op.drop_column('t_qc_item', 'material_list_id')

    # Revert enum
    op.execute("ALTER TABLE t_test_result MODIFY COLUMN session_status ENUM('INPROGRESS','COMPLETED') NOT NULL")
