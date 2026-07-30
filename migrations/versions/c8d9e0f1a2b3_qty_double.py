"""Quantities INT -> DOUBLE — center sends fractional qty.

Center (thaimui_center) stores t_sales_item.quantity and t_material.quantity as
DOUBLE. PMS held every qty as INT, so MySQL rounded on insert (2.5 -> 3). This
widens the whole sales-item and material chain to DOUBLE.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d9e0f1a2b3'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


# (table, column, nullable, server_default)
COLUMNS = [
    # ── sales item chain ──
    ('t_sales_items',              'quantity',            False, None),
    ('t_work_order',               'quantity',            False, '1'),
    ('t_work_run',                 'quantity',            False, '1'),
    ('t_work_run',                 'usable_qty',          True,  None),
    ('t_work_run',                 'qty_from_failed',     True,  None),
    ('t_work_run_transaction',     'quantity',            False, None),
    ('t_work_run_rework_source',   'qty',                 False, None),
    ('t_qc_work_order',            'quantity',            False, '1'),
    ('t_test_result',              'claimed_qty',         False, None),
    ('t_test_result_work_run',     'qty_from_run',        False, None),
    # ── material chain ──
    ('t_material_list',            'quantity',            False, None),
    ('t_material_transaction',     'amount',              False, None),
    ('t_component_material_usage', 'quantity_used',       False, None),
    ('t_picking_request_item',     'quantity',            False, None),
    ('t_work_run_required_item',   'quantity',            False, None),
    ('t_work_run_required_item',   'qty_consumed_actual', True,  None),
    ('t_qc_item',                  'required_qty',        True,  None),
    ('t_test_result_required_item', 'required_qty',       False, None),
    ('t_test_result_required_item', 'qty_consumed_actual', True, None),
]


def _alter(to_type, from_type):
    for table, column, nullable, default in COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=from_type,
            type_=to_type,
            existing_nullable=nullable,
            existing_server_default=sa.text(default) if default else None,
        )


def upgrade():
    _alter(sa.Double(), sa.Integer())


def downgrade():
    # Fractional values are truncated by MySQL on the way back to INT.
    _alter(sa.Integer(), sa.Double())
