"""Item-code autofill: item_decode_segment + item_reference tables.

Backs the Material-Table autofill feature. `item_decode_segment` holds the
positional code-decoder legend value-maps for decodable categories (SLING,
CHAIN); `item_reference` is the flat Item No. -> Item Description lookup for
every other category. Both are refreshed wholesale by admin xlsx upload
(replace-on-upload), so no seed data is emitted here.

Table creation is guarded by an existence check: the autofill tables may be
created directly (outside the alembic chain) on a dev DB that is otherwise
behind head, so this migration must be a no-op when they already exist.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if 'item_decode_segment' not in existing:
        op.create_table(
            'item_decode_segment',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('category', sa.String(length=32), nullable=False),
            sa.Column('segment', sa.String(length=8), nullable=False),
            sa.Column('code', sa.String(length=8), nullable=False),
            sa.Column('field', sa.String(length=32), nullable=False),
            sa.Column('value', sa.String(length=255), nullable=False),
            sa.Column('created_by', sa.String(length=80), nullable=True),
            sa.Column('updated_by', sa.String(length=80), nullable=True),
            sa.Column('created_date', sa.DateTime(), nullable=True),
            sa.Column('updated_date', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('category', 'segment', 'code', 'field',
                                name='uq_item_decode_segment'),
        )
        op.create_index('ix_item_decode_segment_lookup', 'item_decode_segment',
                        ['category', 'segment', 'code'], unique=False)

    if 'item_reference' not in existing:
        op.create_table(
            'item_reference',
            sa.Column('item_no', sa.String(length=64), nullable=False),
            sa.Column('item_description', sa.String(length=500), nullable=True),
            sa.Column('created_by', sa.String(length=80), nullable=True),
            sa.Column('updated_by', sa.String(length=80), nullable=True),
            sa.Column('created_date', sa.DateTime(), nullable=True),
            sa.Column('updated_date', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('item_no'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if 'item_reference' in existing:
        op.drop_table('item_reference')
    if 'item_decode_segment' in existing:
        op.drop_index('ix_item_decode_segment_lookup', table_name='item_decode_segment')
        op.drop_table('item_decode_segment')
