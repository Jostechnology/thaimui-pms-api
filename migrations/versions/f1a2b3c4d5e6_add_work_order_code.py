"""add work_order_code to t_work_order

Revision ID: f1a2b3c4d5e6
Revises: 9f9741fe25d5
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '9f9741fe25d5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('t_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_order_code', sa.String(length=50), nullable=True))

    op.execute("""
        UPDATE t_work_order wo
        JOIN t_sales_items si ON wo.sales_item_id = si.sales_item_id
        JOIN (
            SELECT
                si2.sales_item_id,
                COUNT(*) AS item_order
            FROM t_sales_items si2
            JOIN t_sales_items si3
                ON si3.doc_entry = si2.doc_entry
                AND si3.sales_item_id <= si2.sales_item_id
            GROUP BY si2.sales_item_id
        ) AS ordered ON ordered.sales_item_id = si.sales_item_id
        SET wo.work_order_code = CONCAT(si.doc_num, '-', ordered.item_order)
    """)


def downgrade():
    with op.batch_alter_table('t_work_order', schema=None) as batch_op:
        batch_op.drop_column('work_order_code')
