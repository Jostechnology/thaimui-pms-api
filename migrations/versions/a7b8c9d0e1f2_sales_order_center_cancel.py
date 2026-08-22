"""SalesOrder center cancel: cancel_requested + timestamps.

Center may request an order cancel at any time. PMS acks immediately and puts
the order into a drain-pending state: `cancel_requested` blocks new forward
work (runs/tests/picking) while in-flight work finishes, and
`cancel_completed_date` is stamped when the drain empties (terminal).
`cancel_requested_date` records when center asked. Stop-forward only — no WMS
reversal, so no data migration of existing stock/output.

Existing rows default to not-cancelled (server_default '0').

Revision ID: a7b8c9d0e1f2
Revises: 4f7ecb6f8fe5
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = '4f7ecb6f8fe5'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: MySQL DDL auto-commits per statement, so guard each add so a
    # rerun after a mid-flight crash converges to the target state.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('t_sales_order')}

    with op.batch_alter_table('t_sales_order') as batch_op:
        if 'cancel_requested' not in existing:
            batch_op.add_column(sa.Column(
                'cancel_requested', sa.Boolean(),
                nullable=False, server_default='0',
            ))
        if 'cancel_requested_date' not in existing:
            batch_op.add_column(sa.Column('cancel_requested_date', sa.DateTime(), nullable=True))
        if 'cancel_completed_date' not in existing:
            batch_op.add_column(sa.Column('cancel_completed_date', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('t_sales_order')}

    with op.batch_alter_table('t_sales_order') as batch_op:
        if 'cancel_completed_date' in existing:
            batch_op.drop_column('cancel_completed_date')
        if 'cancel_requested_date' in existing:
            batch_op.drop_column('cancel_requested_date')
        if 'cancel_requested' in existing:
            batch_op.drop_column('cancel_requested')
