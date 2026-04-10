"""rename item_num to quantity in t_sales_item

Revision ID: 799e62318802
Revises: a1b2c3d4e5f7
Create Date: 2026-04-10 01:57:50.068228

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '799e62318802'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def _col_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.scalar() > 0


def upgrade():
    conn = op.get_bind()
    with op.batch_alter_table('t_sales_items', schema=None) as batch_op:
        if _col_exists(conn, 't_sales_items', 'item_num'):
            batch_op.alter_column('item_num', new_column_name='quantity', existing_type=sa.Integer(), nullable=False)
        if not _col_exists(conn, 't_sales_items', 'order_line_num'):
            batch_op.add_column(sa.Column('order_line_num', sa.Integer(), nullable=True))
        if not _col_exists(conn, 't_sales_items', 'unit_code'):
            batch_op.add_column(sa.Column('unit_code', sa.String(28), nullable=True))


def downgrade():
    conn = op.get_bind()
    with op.batch_alter_table('t_sales_items', schema=None) as batch_op:
        if _col_exists(conn, 't_sales_items', 'unit_code'):
            batch_op.drop_column('unit_code')
        if _col_exists(conn, 't_sales_items', 'order_line_num'):
            batch_op.drop_column('order_line_num')
        if _col_exists(conn, 't_sales_items', 'quantity'):
            batch_op.alter_column('quantity', new_column_name='item_num', existing_type=sa.Integer(), nullable=False)

    # ### end Alembic commands ###
