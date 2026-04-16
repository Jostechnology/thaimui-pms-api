"""add t_work_run_required_item and t_work_run_picking_item

Revision ID: j5e6f7g8h9i0
Revises: i4d5e6f7g8h9
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'j5e6f7g8h9i0'
down_revision = 'i4d5e6f7g8h9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        't_work_run_required_item',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(),
                  sa.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('material_list_id', sa.Integer(),
                  sa.ForeignKey('t_material_list.material_list_id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_code', sa.String(100), nullable=False),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('branch_id', sa.Integer(),
                  sa.ForeignKey('m_branch.branch_id'), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
    )

    op.create_table(
        't_work_run_picking_item',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('work_run_id', sa.Integer(),
                  sa.ForeignKey('t_work_run.work_run_id', ondelete='CASCADE'), nullable=False),
        sa.Column('picking_request_item_id', sa.Integer(),
                  sa.ForeignKey('t_picking_request_item.picking_request_item_id', ondelete='CASCADE'), nullable=False),
        sa.Column('qty_consumed', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('t_work_run_picking_item')
    op.drop_table('t_work_run_required_item')
