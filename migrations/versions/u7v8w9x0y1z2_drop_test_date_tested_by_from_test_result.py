"""Drop test_date and tested_by from t_test_result

Revision ID: u7v8w9x0y1z2
Revises: t6u7v8w9x0y1
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
from sqlalchemy import text

revision = 'u7v8w9x0y1z2'
down_revision = 't6u7v8w9x0y1'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    result = op.get_bind().execute(
        text("SELECT COUNT(*) FROM information_schema.columns "
             "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"),
        {'t': table, 'c': column}
    )
    return result.scalar() > 0


def upgrade():
    if _column_exists('t_test_result', 'test_date'):
        op.drop_column('t_test_result', 'test_date')
    if _column_exists('t_test_result', 'tested_by'):
        op.drop_column('t_test_result', 'tested_by')


def downgrade():
    import sqlalchemy as sa
    op.add_column('t_test_result', sa.Column('tested_by', sa.String(length=100), nullable=True))
    op.add_column('t_test_result', sa.Column('test_date', sa.DateTime(), nullable=True))
