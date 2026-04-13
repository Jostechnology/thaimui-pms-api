"""rework picking request to sales-order level

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2026-04-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'i4d5e6f7g8h9'
down_revision = 'h3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade():
    # --- t_picking_request: remove entity-specific columns ---
    op.drop_constraint('fk_picking_request_work_run', 't_picking_request', type_='foreignkey')
    op.drop_column('t_picking_request', 'work_run_id')

    op.drop_constraint('fk_picking_request_test_result', 't_picking_request', type_='foreignkey')
    op.drop_column('t_picking_request', 'test_result_id')

    op.drop_column('t_picking_request', 'request_type')

    # --- t_picking_request_item: add sales_item_id and material_list_id ---
    op.add_column('t_picking_request_item',
        sa.Column('sales_item_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_pri_sales_item',
        't_picking_request_item', 't_sales_items',
        ['sales_item_id'], ['sales_item_id'],
        ondelete='SET NULL'
    )
    op.add_column('t_picking_request_item',
        sa.Column('material_list_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_pri_material_list',
        't_picking_request_item', 't_material_list',
        ['material_list_id'], ['material_list_id'],
        ondelete='SET NULL'
    )

    # --- Create t_test_result_picking_item (replaces t_test_result_picking_request) ---
    op.create_table(
        't_test_result_picking_item',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('test_result_id', sa.Integer(), sa.ForeignKey('t_test_result.test_result_id', ondelete='CASCADE'), nullable=False),
        sa.Column('picking_request_item_id', sa.Integer(), sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='CASCADE'), nullable=False),
        sa.Column('qty_consumed', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('t_test_result_picking_item')

    op.drop_constraint('fk_pri_material_list', 't_picking_request_item', type_='foreignkey')
    op.drop_column('t_picking_request_item', 'material_list_id')
    op.drop_constraint('fk_pri_sales_item', 't_picking_request_item', type_='foreignkey')
    op.drop_column('t_picking_request_item', 'sales_item_id')

    op.add_column('t_picking_request',
        sa.Column('request_type', sa.Enum('WORK_RUN', 'TEST_RESULT', name='pickingrequesttype'), nullable=False, server_default='WORK_RUN')
    )
    op.add_column('t_picking_request',
        sa.Column('work_run_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_picking_request_work_run',
        't_picking_request', 't_work_run',
        ['work_run_id'], ['work_run_id'],
        ondelete='SET NULL'
    )
    op.add_column('t_picking_request',
        sa.Column('test_result_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_picking_request_test_result',
        't_picking_request', 't_test_result',
        ['test_result_id'], ['test_result_id'],
        ondelete='SET NULL'
    )
