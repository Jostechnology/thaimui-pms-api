"""Drop picking usage-tracking layer — WMS is the stock source of truth.

Removes consumption/adjustment tables and verify/reallocation columns:
- t_test_result_picking_item
- t_work_run_picking_item
- t_picking_item_adjustment
- t_picking_request_item.qty_received_actual
- t_picking_request.is_reallocation

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c8d9e0f1a2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('t_test_result_picking_item')
    op.drop_table('t_work_run_picking_item')
    op.drop_table('t_picking_item_adjustment')
    op.drop_column('t_picking_request_item', 'qty_received_actual')
    op.drop_column('t_picking_request', 'is_reallocation')


def downgrade():
    op.add_column('t_picking_request', sa.Column('is_reallocation', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('t_picking_request_item', sa.Column('qty_received_actual', sa.Integer(), nullable=True))
    op.create_table(
        't_picking_item_adjustment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('picking_request_item_id', sa.Integer(), sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='CASCADE'), nullable=False),
        sa.Column('delta_qty', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Enum('MISCOUNT', 'SPILLAGE', 'CORRECTION', 'REALLOCATE', 'OTHER', name='pickingitemadjustmentreason'), nullable=False),
        sa.Column('remark', sa.String(500), nullable=True),
        sa.Column('counterparty_picking_request_item_id', sa.Integer(), sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=True),
    )
    op.create_table(
        't_work_run_picking_item',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('work_run_id', sa.Integer(), sa.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('picking_request_item_id', sa.Integer(), sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='CASCADE'), nullable=False),
        sa.Column('work_run_required_item_id', sa.Integer(), sa.ForeignKey('t_work_run_required_item.id', ondelete='SET NULL'), nullable=True),
        sa.Column('qty_allocated', sa.Integer(), nullable=False),
        sa.Column('qty_consumed', sa.Integer(), nullable=True),
        sa.Column('allocation_mode', sa.Enum('AUTO', 'MANUAL', name='allocationmode'), nullable=False),
    )
    op.create_table(
        't_test_result_picking_item',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('test_result_id', sa.Integer(), sa.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False),
        sa.Column('picking_request_item_id', sa.Integer(), sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_result_required_item_id', sa.Integer(), sa.ForeignKey('t_test_result_required_item.id', ondelete='SET NULL'), nullable=True),
        sa.Column('qty_allocated', sa.Integer(), nullable=False),
        sa.Column('qty_consumed', sa.Integer(), nullable=True),
        sa.Column('allocation_mode', sa.Enum('AUTO', 'MANUAL', name='allocationmode'), nullable=False),
    )
