"""rename item_num to original_num in t_material_list

Revision ID: a9f1b2c3d4e5
Revises: 3c4afddf9fbb
Create Date: 2026-03-09

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a9f1b2c3d4e5'
down_revision = '3c4afddf9fbb'
branch_labels = None
depends_on = None


import sqlalchemy as sa

def upgrade():
    op.alter_column(
        't_material_list',
        'item_num',
        new_column_name='original_num',
        existing_type=sa.Integer()
    )


def downgrade():
    op.alter_column(
        't_material_list',
        'original_num',
        new_column_name='item_num',
        existing_type=sa.Integer()
    )
