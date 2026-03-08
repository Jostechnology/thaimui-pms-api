"""cert_link_to_sales_order

Revision ID: a1b2c3d4e5f6
Revises: 596848cb2e8c
Create Date: 2026-03-07 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from migrations.utils import column_exists


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '596848cb2e8c'
branch_labels = None
depends_on = None


def upgrade():
    # Add po_number to t_sales_order
    with op.batch_alter_table('t_sales_order', schema=None) as batch_op:
        if not column_exists('t_sales_order', 'po_number'):
            batch_op.add_column(sa.Column('po_number', sa.String(length=100), nullable=True))

    # Replace qc_work_order_id with doc_entry on t_qc_certification
    with op.batch_alter_table('t_qc_certification', schema=None) as batch_op:
        if not column_exists('t_qc_certification', 'doc_entry'):
            batch_op.add_column(sa.Column('doc_entry', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_qc_cert_sales_order', 't_sales_order', ['doc_entry'], ['doc_entry'], ondelete='CASCADE')

    # Migrate existing data: set doc_entry from the sales item linked via qc_work_order
    op.execute("""
        UPDATE t_qc_certification c
        JOIN t_qc_work_order wo ON wo.qc_work_order_id = c.qc_work_order_id
        JOIN t_sales_items si ON si.sales_item_id = wo.sales_item_id
        SET c.doc_entry = si.doc_entry
        WHERE c.doc_entry IS NULL
    """)

    # Make doc_entry non-nullable after migration
    with op.batch_alter_table('t_qc_certification', schema=None) as batch_op:
        batch_op.drop_constraint('t_qc_certification_ibfk_1', type_='foreignkey')  # drop first
        batch_op.drop_column('qc_work_order_id')
        batch_op.drop_constraint('fk_qc_cert_sales_order', type_='foreignkey')  # drop first

        batch_op.alter_column('doc_entry', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_qc_cert_sales_order', 't_sales_order', ['doc_entry'], ['doc_entry'], ondelete='CASCADE')  # re-add

    # Add sales_item_id to t_qc_check_item
    with op.batch_alter_table('t_qc_check_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sales_item_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_qc_check_item_sales_item', 't_sales_items', ['sales_item_id'], ['sales_item_id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('t_qc_check_item', schema=None) as batch_op:
        batch_op.drop_constraint('fk_qc_check_item_sales_item', type_='foreignkey')
        batch_op.drop_column('sales_item_id')

    with op.batch_alter_table('t_qc_certification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('qc_work_order_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('t_qc_certification_ibfk_1', 't_qc_work_order', ['qc_work_order_id'], ['qc_work_order_id'], ondelete='CASCADE')
        batch_op.drop_constraint('fk_qc_cert_sales_order', type_='foreignkey')
        batch_op.drop_column('doc_entry')

    with op.batch_alter_table('t_sales_order', schema=None) as batch_op:
        batch_op.drop_column('po_number')
