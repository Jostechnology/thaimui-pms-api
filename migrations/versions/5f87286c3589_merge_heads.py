"""merge heads

Revision ID: 5f87286c3589
Revises: 579c996d6dcb, b2c3d4e5f6a7
Create Date: 2026-03-09 11:54:48.455698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f87286c3589'
down_revision = ('579c996d6dcb', 'b2c3d4e5f6a7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
