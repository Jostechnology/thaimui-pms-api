"""Add started_at column to t_test_result

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 't6u7v8w9x0y1'
down_revision = 's5t6u7v8w9x0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('t_test_result', sa.Column('started_at', sa.DateTime(), nullable=True))
    # Backfill existing INPROGRESS/PAUSED/COMPLETED rows that were started before this column existed
    op.execute("""
        UPDATE t_test_result
        SET started_at = updated_date
        WHERE session_status IN ('INPROGRESS', 'PAUSED', 'COMPLETED')
          AND started_at IS NULL
    """)


def downgrade():
    op.drop_column('t_test_result', 'started_at')
