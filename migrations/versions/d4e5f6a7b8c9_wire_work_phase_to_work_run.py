"""Wire WorkPhase to WorkRun instead of WorkOrder; move current_phase to WorkRun

Revision ID: d4e5f6a7b8c9
Revises: 9a7ea6cd30c6
Create Date: 2026-03-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '9a7ea6cd30c6'
branch_labels = None
depends_on = None


def _get_fk_name(table_name, column_name):
    """Return the FK constraint name for a given column, or None if not found."""
    conn = op.get_bind()
    inspector = inspect(conn)
    for fk in inspector.get_foreign_keys(table_name):
        if column_name in fk.get('constrained_columns', []):
            return fk['name']
    return None


def upgrade():
    conn = op.get_bind()

    # Step 1: Add work_run_id (nullable) to t_work_phase
    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_run_id', sa.Integer(), nullable=True))
        # batch_op.create_foreign_key(
        #     'fk_work_phase_work_run_id',
        #     't_work_run', ['work_run_id'], ['work_run_id'],
        #     ondelete='CASCADE'
        # )

    # Step 2: Data migration — assign each phase to the oldest WorkRun of its WorkOrder.
    # Phases with no matching WorkRun are left NULL (edge case; they become orphaned).
    conn.execute(text("""
        START TRANSACTION;

        INSERT INTO t_work_run (work_order_id, quantity)
        SELECT wo.work_order_id, 1
        FROM t_work_order wo
        LEFT JOIN t_work_run wr ON wr.work_order_id = wo.work_order_id
        WHERE wr.work_order_id IS NULL;

        UPDATE t_work_phase wp
        JOIN (
            SELECT work_order_id, MIN(work_run_id) AS first_run_id
            FROM t_work_run
            GROUP BY work_order_id
        ) r ON r.work_order_id = wp.work_order_id
        SET wp.work_run_id = r.first_run_id
        WHERE wp.work_run_id IS NULL;

        COMMIT;
    """))
    
    # Step 3: Make work_run_id NOT NULL now that data is populated
    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        batch_op.alter_column('work_run_id', existing_type=sa.Integer(), nullable=False)
    
    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_work_phase_work_run_id',
            't_work_run', ['work_run_id'], ['work_run_id'],
            ondelete='CASCADE'
        )

    # Step 4: Drop old FK on t_work_phase.work_order_id, then drop column
    fk_phase_order = _get_fk_name('t_work_phase', 'work_order_id')
    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        if fk_phase_order:
            batch_op.drop_constraint(fk_phase_order, type_='foreignkey')
        batch_op.drop_column('work_order_id')

    # Step 5: Add current_phase_id (nullable) to t_work_run
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_phase_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_work_run_current_phase_id',
            't_work_phase', ['current_phase_id'], ['work_phase_id']
        )

    # Step 6: Drop old current_phase_id FK and column from t_work_order
    fk_order_phase = _get_fk_name('t_work_order', 'current_phase_id')
    with op.batch_alter_table('t_work_order', schema=None) as batch_op:
        if fk_order_phase:
            batch_op.drop_constraint(fk_order_phase, type_='foreignkey')
        batch_op.drop_column('current_phase_id')


def downgrade():
    conn = op.get_bind()

    # Restore current_phase_id on t_work_order (nullable, no data recovery)
    with op.batch_alter_table('t_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_phase_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_work_order_current_phase_id',
            't_work_phase', ['current_phase_id'], ['work_phase_id']
        )

    # Remove current_phase_id from t_work_run
    with op.batch_alter_table('t_work_run', schema=None) as batch_op:
        batch_op.drop_constraint('fk_work_run_current_phase_id', type_='foreignkey')
        batch_op.drop_column('current_phase_id')

    # Restore work_order_id on t_work_phase
    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        batch_op.add_column(sa.Column('work_order_id', sa.Integer(), nullable=True))

    # Data migration back — derive work_order_id from work_run
    conn.execute(text("""
        UPDATE t_work_phase wp
        JOIN t_work_run wr ON wr.work_run_id = wp.work_run_id
        SET wp.work_order_id = wr.work_order_id
    """))

    with op.batch_alter_table('t_work_phase', schema=None) as batch_op:
        batch_op.alter_column('work_order_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_work_phase_work_order_id',
            't_work_order', ['work_order_id'], ['work_order_id']
        )
        batch_op.drop_constraint('fk_work_phase_work_run_id', type_='foreignkey')
        batch_op.drop_column('work_run_id')
