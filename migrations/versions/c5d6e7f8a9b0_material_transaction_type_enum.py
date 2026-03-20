"""material-transaction-type-enum

Revision ID: c5d6e7f8a9b0
Revises: b4f2a3e6d7c8
Create Date: 2026-03-19 00:00:00.000000

Change t_material_transaction.type from VARCHAR to ENUM('INIT','ADD','REMOVE').
Also allows negative amounts so REMOVE transactions store signed values.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c5d6e7f8a9b0'
down_revision = 'b4f2a3e6d7c8'
branch_labels = None
depends_on = None


def upgrade():
    # Migrate existing 'ADD'/'REMOVE' string values to the new enum.
    # Existing rows that were 'ADD'/'REMOVE' map 1-to-1; no INIT rows exist yet.
    op.execute("""
        ALTER TABLE t_material_transaction
        MODIFY COLUMN type ENUM('INIT', 'ADD', 'REMOVE') NOT NULL
    """)

    # Make amount signed so REMOVE transactions can store negative values.
    op.execute("""
        ALTER TABLE t_material_transaction
        MODIFY COLUMN amount INT NOT NULL
    """)

    # Flip existing REMOVE rows to negative amounts.
    op.execute("""
        UPDATE t_material_transaction
        SET amount = -ABS(amount)
        WHERE type = 'REMOVE'
    """)


def downgrade():
    # Restore positive amounts for REMOVE rows before converting type back.
    op.execute("""
        UPDATE t_material_transaction
        SET amount = ABS(amount)
        WHERE type = 'REMOVE'
    """)

    op.execute("""
        ALTER TABLE t_material_transaction
        MODIFY COLUMN type VARCHAR(24) NOT NULL
    """)
