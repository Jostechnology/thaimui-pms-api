"""Add PAUSED to TestSessionStatus enum

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-04-29 00:00:00.000000

"""
from alembic import op

revision = 'r4s5t6u7v8w9'
down_revision = 'q3r4s5t6u7v8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE t_test_result MODIFY COLUMN session_status "
        "ENUM('PENDING','INPROGRESS','PAUSED','COMPLETED') NOT NULL"
    )


def downgrade():
    op.execute(
        "ALTER TABLE t_test_result MODIFY COLUMN session_status "
        "ENUM('PENDING','INPROGRESS','COMPLETED') NOT NULL"
    )
