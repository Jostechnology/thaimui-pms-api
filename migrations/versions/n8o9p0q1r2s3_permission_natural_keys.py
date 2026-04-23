"""unique module_code and (module_id, method) for seed upsert

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-04-23 00:00:00.000000

"""
from alembic import op


revision = 'n8o9p0q1r2s3'
down_revision = 'm7n8o9p0q1r2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('uq_module_code', 'm_module', ['module_code'])
    op.create_unique_constraint(
        'uq_permission_module_method', 'm_permission', ['module_id', 'method']
    )


def downgrade():
    op.drop_constraint('uq_permission_module_method', 'm_permission', type_='unique')
    op.drop_constraint('uq_module_code', 'm_module', type_='unique')
