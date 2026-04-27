"""backfill depreciation and maintenance rates for existing work_run_machine rows

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-04-27 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'p2q3r4s5t6u7'
down_revision = 'o1p2q3r4s5t6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Fetch all existing machine entries joined with machine config
    rows = conn.execute(sa.text("""
        SELECT
            wrm.work_run_machine_id,
            wrm.machine_id,
            wrm.from_time,
            wrm.to_time,
            m.purchase_price,
            m.useful_life_years,
            m.working_hours_per_day,
            m.remaining_maintenance_cost,
            m.is_second_hand,
            m.accumulated_hours
        FROM t_work_run_machine wrm
        JOIN m_machine m ON m.machine_id = wrm.machine_id
        WHERE wrm.depreciation_per_second = 0
    """)).fetchall()

    for row in rows:
        # ── Depreciation rate (same formula as service) ──
        dep_rate = 0.0
        pp = row.purchase_price or 0
        uly = row.useful_life_years or 0
        whpd = row.working_hours_per_day or 0
        if pp > 0 and uly > 0 and whpd > 0:
            total_sec = uly * 365 * whpd * 3600
            if total_sec > 0:
                dep_rate = pp / total_sec

        # ── Maintenance rate ──
        # Use same logic: remaining_maintenance_cost / total_past_seconds
        # Here we can only approximate using existing history in the DB
        maint_rate = 0.0
        remaining = row.remaining_maintenance_cost or 0
        if remaining > 0:
            history = conn.execute(sa.text("""
                SELECT COALESCE(SUM(GREATEST(0, TIMESTAMPDIFF(SECOND, from_time, to_time))), 0)
                FROM t_work_run_machine
                WHERE machine_id = :mid AND to_time IS NOT NULL
            """), {"mid": row.machine_id}).scalar() or 0

            accumulated_sec = (row.accumulated_hours or 0) * 3600 if row.is_second_hand else 0
            total_past_sec = float(history) + accumulated_sec
            if total_past_sec > 0:
                maint_rate = remaining / total_past_sec

        # ── Finalized costs for closed machine entries ──
        dep_cost = None
        maint_cost = None
        if row.to_time and row.from_time:
            # Get breaks for this work run
            work_run_id_row = conn.execute(sa.text(
                "SELECT work_run_id FROM t_work_run_machine WHERE work_run_machine_id = :id"
            ), {"id": row.work_run_machine_id}).scalar()

            break_sec = conn.execute(sa.text("""
                SELECT COALESCE(SUM(
                    GREATEST(0, TIMESTAMPDIFF(SECOND,
                        GREATEST(break_start, :mstart),
                        LEAST(COALESCE(break_end, :mend), :mend)
                    ))
                ), 0)
                FROM t_work_run_break
                WHERE work_run_id = :wrid
                  AND break_start < :mend
                  AND (break_end IS NULL OR break_end > :mstart)
            """), {
                "wrid": work_run_id_row,
                "mstart": row.from_time,
                "mend": row.to_time,
            }).scalar() or 0

            total_sec = max(0, (row.to_time - row.from_time).total_seconds()) if hasattr(row.to_time, 'total_seconds') else 0
            if not hasattr(row.to_time, 'total_seconds'):
                import datetime
                if isinstance(row.to_time, datetime.datetime) and isinstance(row.from_time, datetime.datetime):
                    total_sec = max(0, (row.to_time - row.from_time).total_seconds())

            entry_sec = max(0, total_sec - float(break_sec))
            dep_cost = round(dep_rate * entry_sec, 6)
            alloc = min(maint_rate * entry_sec, remaining)
            maint_cost = round(alloc, 6)

        conn.execute(sa.text("""
            UPDATE t_work_run_machine
            SET depreciation_per_second = :dep_rate,
                maintenance_rate_per_second = :maint_rate,
                depreciation_cost = :dep_cost,
                maintenance_cost = :maint_cost
            WHERE work_run_machine_id = :id
        """), {
            "dep_rate": dep_rate,
            "maint_rate": maint_rate,
            "dep_cost": dep_cost,
            "maint_cost": maint_cost,
            "id": row.work_run_machine_id,
        })

    # ── Backfill t_work_run_cost for COMPLETED work runs ──
    completed_runs = conn.execute(sa.text("""
        SELECT wr.work_run_id, wr.start_date, wr.end_date
        FROM t_work_run wr
        WHERE wr.status = 'COMPLETED'
          AND NOT EXISTS (
              SELECT 1 FROM t_work_run_cost c WHERE c.work_run_id = wr.work_run_id
          )
    """)).fetchall()

    for run in completed_runs:
        # Material cost
        material_cost = conn.execute(sa.text("""
            SELECT COALESCE(SUM(
                (CASE WHEN ml.quantity > 0 THEN ml.cost_price / ml.quantity ELSE 0 END) * ri.quantity
            ), 0)
            FROM t_work_run_required_item ri
            JOIN t_material_list ml ON ml.material_list_id = ri.material_list_id
            WHERE ri.work_run_id = :wrid
        """), {"wrid": run.work_run_id}).scalar() or 0

        # Machine costs (sum from finalized machine entries)
        machine_costs = conn.execute(sa.text("""
            SELECT
                COALESCE(SUM(depreciation_cost), 0) AS dep,
                COALESCE(SUM(maintenance_cost), 0) AS maint
            FROM t_work_run_machine
            WHERE work_run_id = :wrid AND to_time IS NOT NULL
        """), {"wrid": run.work_run_id}).fetchone()
        dep_total = float(machine_costs.dep or 0)
        maint_total = float(machine_costs.maint or 0)

        # Labor cost
        labor_cost = conn.execute(sa.text("""
            SELECT COALESCE(SUM(
                (e.salary_base / 30.0 / 8.0 / 3600.0)
                * GREATEST(0, TIMESTAMPDIFF(SECOND, wa.from_time, COALESCE(wa.to_time, :end_date)))
            ), 0)
            FROM t_work_run_assignment wa
            JOIN m_employee e ON e.employee_id = wa.employee_id
            WHERE wa.work_run_id = :wrid
        """), {"wrid": run.work_run_id, "end_date": run.end_date}).scalar() or 0

        total = round(float(material_cost) + dep_total + maint_total + float(labor_cost), 6)

        conn.execute(sa.text("""
            INSERT INTO t_work_run_cost
                (work_run_id, material_cost, depreciation_cost, maintenance_cost, labor_cost, total_cost, created_date, updated_date)
            VALUES
                (:wrid, :mat, :dep, :maint, :labor, :total, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                material_cost = VALUES(material_cost),
                depreciation_cost = VALUES(depreciation_cost),
                maintenance_cost = VALUES(maintenance_cost),
                labor_cost = VALUES(labor_cost),
                total_cost = VALUES(total_cost),
                updated_date = NOW()
        """), {
            "wrid": run.work_run_id,
            "mat": round(float(material_cost), 6),
            "dep": round(dep_total, 6),
            "maint": round(maint_total, 6),
            "labor": round(float(labor_cost), 6),
            "total": total,
        })


def downgrade():
    # Reset rates to 0 (cannot recover original data)
    op.execute("UPDATE t_work_run_machine SET depreciation_per_second = 0, maintenance_rate_per_second = 0, depreciation_cost = NULL, maintenance_cost = NULL")
    op.execute("DELETE FROM t_work_run_cost")
