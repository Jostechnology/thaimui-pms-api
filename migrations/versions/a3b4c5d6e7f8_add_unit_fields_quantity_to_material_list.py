"""add unit_name, unit_id, quantity to t_material_list

Revision ID: a3b4c5d6e7f8
Revises: 799e62318802
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = '799e62318802'
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
    with op.batch_alter_table('t_material_list', schema=None) as batch_op:
        if _col_exists(conn, 't_material_list', 'original_num'):
            batch_op.alter_column('original_num', new_column_name='quantity', existing_type=sa.Integer(), nullable=False)
        if not _col_exists(conn, 't_material_list', 'unit_name'):
            batch_op.add_column(sa.Column('unit_name', sa.String(28), nullable=False, server_default='Piece'))
        if not _col_exists(conn, 't_material_list', 'unit_id'):
            batch_op.add_column(sa.Column('unit_id', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    conn = op.get_bind()
    with op.batch_alter_table('t_material_list', schema=None) as batch_op:
        if _col_exists(conn, 't_material_list', 'unit_id'):
            batch_op.drop_column('unit_id')
        if _col_exists(conn, 't_material_list', 'unit_name'):
            batch_op.drop_column('unit_name')
        if _col_exists(conn, 't_material_list', 'quantity'):
            batch_op.alter_column('quantity', new_column_name='original_num', existing_type=sa.Integer(), nullable=False)
