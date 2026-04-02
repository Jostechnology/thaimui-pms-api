"""add doc_version to t_item_component

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2026-04-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h3c4d5e6f7g8'
down_revision = 'g2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('t_item_component', schema=None) as batch_op:
        batch_op.add_column(sa.Column('doc_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('t_item_component', schema=None) as batch_op:
        batch_op.drop_column('doc_version')
