"""add qc_work_order_code to t_qc_work_order

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-31 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('t_qc_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('qc_work_order_code', sa.String(length=50), nullable=True))

    op.execute("""
        UPDATE t_qc_work_order qc
        JOIN t_sales_items si ON qc.sales_item_id = si.sales_item_id
        JOIN (
            SELECT
                si2.sales_item_id,
                COUNT(*) AS item_order
            FROM t_sales_items si2
            JOIN t_sales_items si3
                ON si3.doc_entry = si2.doc_entry
                AND si3.sales_item_id <= si2.sales_item_id
            GROUP BY si2.sales_item_id
        ) AS item_ordered ON item_ordered.sales_item_id = si.sales_item_id
        JOIN (
            SELECT
                qc2.qc_work_order_id,
                COUNT(*) AS qc_order
            FROM t_qc_work_order qc2
            JOIN t_qc_work_order qc3
                ON qc3.sales_item_id = qc2.sales_item_id
                AND qc3.qc_work_order_id <= qc2.qc_work_order_id
            GROUP BY qc2.qc_work_order_id
        ) AS qc_ordered ON qc_ordered.qc_work_order_id = qc.qc_work_order_id
        SET qc.qc_work_order_code = CONCAT(si.doc_num, '-', item_ordered.item_order, '-', qc_ordered.qc_order)
    """)


def downgrade():
    with op.batch_alter_table('t_qc_work_order', schema=None) as batch_op:
        batch_op.drop_column('qc_work_order_code')
