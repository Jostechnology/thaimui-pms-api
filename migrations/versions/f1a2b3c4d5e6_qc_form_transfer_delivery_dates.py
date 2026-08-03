"""QCForm gains transfer_date and delivery_date, split off customer_receipt_number.

The frontend bound a single state field (customerReceiptNumber) to BOTH the
"วันที่ย้าย" (transfer date) and "วันที่ส่ง" (delivery date) inputs, so editing
one silently overwrote the other, and whichever value won last was persisted
into t_qc_form.customer_receipt_number — a String(100) meant for an actual
receipt number, not a date.

transfer_date and delivery_date are new, independent, nullable Date columns.
customer_receipt_number is left untouched and reverts to meaning an actual
receipt number.

No backfill: existing customer_receipt_number values are ambiguous garbage —
they could be either a transfer date or a delivery date, in whatever format
the frontend happened to send at the time — and guessing which is which (or
parsing them at all) would corrupt data rather than recover it. Both new
columns start NULL for every existing row.

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'e0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('t_qc_form', sa.Column('transfer_date', sa.Date(), nullable=True))
    op.add_column('t_qc_form', sa.Column('delivery_date', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('t_qc_form', 'delivery_date')
    op.drop_column('t_qc_form', 'transfer_date')
