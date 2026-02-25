"""change qc_work_order fk to sales_item_id

Revision ID: ad561750863e
Revises: 8e529a9295d1
Create Date: 2026-02-25 14:58:38.460150

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ad561750863e'
down_revision = '8e529a9295d1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Drop FK constraint (ถ้ายังมีอยู่)
    try:
        conn.execute(sa.text("ALTER TABLE t_qc_work_order DROP FOREIGN KEY t_qc_work_order_ibfk_1"))
    except Exception:
        pass  # ถูก drop ไปแล้ว

    # 2. Drop unique index on work_order_id (ถ้ายังมีอยู่)
    try:
        conn.execute(sa.text("ALTER TABLE t_qc_work_order DROP INDEX work_order_id"))
    except Exception:
        pass  # ถูก drop ไปแล้ว

    # 3. Drop work_order_id column (ถ้ายังมีอยู่)
    try:
        conn.execute(sa.text("ALTER TABLE t_qc_work_order DROP COLUMN work_order_id"))
    except Exception:
        pass  # ถูก drop ไปแล้ว

    # 4. Add sales_item_id column (ถ้ายังไม่มี)
    result = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_NAME='t_qc_work_order' AND COLUMN_NAME='sales_item_id'
        AND TABLE_SCHEMA=DATABASE()
    """))
    if result.scalar() == 0:
        conn.execute(sa.text(
            "ALTER TABLE t_qc_work_order ADD COLUMN sales_item_id INTEGER NOT NULL DEFAULT 0"
        ))

    # 5. Add FK constraint (ถ้ายังไม่มี)
    try:
        conn.execute(sa.text("""
            ALTER TABLE t_qc_work_order
            ADD CONSTRAINT fk_qc_work_order_sales_item
            FOREIGN KEY (sales_item_id) REFERENCES t_sales_items(sales_item_id)
            ON DELETE CASCADE
        """))
    except Exception:
        pass  # FK มีอยู่แล้ว


def downgrade():
    with op.batch_alter_table('t_qc_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_order_id', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.drop_constraint('fk_qc_work_order_sales_item', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('t_qc_work_order_ibfk_1'), 't_work_order', ['work_order_id'], ['work_order_id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('work_order_id'), ['work_order_id'], unique=True)
        batch_op.drop_column('sales_item_id')
