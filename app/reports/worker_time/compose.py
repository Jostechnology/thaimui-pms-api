"""Compose worker-time report."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.app import db
from app.con_sqlalchemy import (
    Employee, WorkRun, WorkRunAssignment, WorkRunBreak,
)
from app.utils import convert_start_date, convert_end_date


def _seconds_between(a, b):
    if not a or not b:
        return 0
    return max(0, int((b - a).total_seconds()))


def _overlap_seconds(a_start, a_end, b_start, b_end):
    if not all([a_start, a_end, b_start, b_end]):
        return 0
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0
    return int((end - start).total_seconds())


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    employee_id = params.get("employee_id")

    a_query = (
        db.session.query(WorkRunAssignment)
        .options(joinedload(WorkRunAssignment.work_run), joinedload(WorkRunAssignment.employee))
        .filter(WorkRunAssignment.from_time >= start, WorkRunAssignment.from_time <= end)
    )
    if employee_id:
        a_query = a_query.filter(WorkRunAssignment.employee_id == employee_id)

    assignments = a_query.order_by(WorkRunAssignment.from_time.asc()).all()
    if not assignments:
        return {"summary": _empty_summary(params), "rows": [], "gantt": [], "employee_totals": [], "breakdown": {"by_day_hours": []}}

    work_run_ids = {a.work_run_id for a in assignments}
    breaks_by_wr = defaultdict(list)
    if work_run_ids:
        breaks = (
            db.session.query(WorkRunBreak)
            .filter(WorkRunBreak.work_run_id.in_(work_run_ids))
            .all()
        )
        for b in breaks:
            breaks_by_wr[b.work_run_id].append(b)

    rows = []
    gantt = []
    totals_by_emp = defaultdict(lambda: {"assignments": 0, "gross_seconds": 0, "net_seconds": 0, "work_runs": set()})
    net_seconds_by_day = defaultdict(int)

    now = datetime.now()
    for a in assignments:
        emp = a.employee
        emp_name = f"{emp.employee_first_name} {emp.employee_last_name}" if emp else "(unknown)"
        wr = a.work_run
        wr_label = wr.lot_number if wr and wr.lot_number else (f"WR#{a.work_run_id}" if a.work_run_id else "-")
        from_t = a.from_time
        to_t = a.to_time or now
        gross = _seconds_between(from_t, to_t)
        # subtract overlapping breaks for same WorkRun
        break_overlap = 0
        for b in breaks_by_wr.get(a.work_run_id, []):
            break_overlap += _overlap_seconds(from_t, to_t, b.break_start, b.break_end or now)
        net = max(0, gross - break_overlap)
        if from_t:
            net_seconds_by_day[from_t.date().isoformat()] += net

        rows.append({
            "assignment_id": a.work_run_assignment_id,
            "employee_id": a.employee_id,
            "employee_name": emp_name,
            "work_run_id": a.work_run_id,
            "lot_number": wr.lot_number if wr else None,
            "from_time": from_t.isoformat() if from_t else None,
            "to_time": a.to_time.isoformat() if a.to_time else None,
            "gross_hours": round(gross / 3600.0, 2),
            "break_hours": round(break_overlap / 3600.0, 2),
            "net_hours": round(net / 3600.0, 2),
            "open": a.to_time is None,
        })

        gantt.append({
            "id": f"a-{a.work_run_assignment_id}",
            "name": f"{emp_name} — {wr_label}",
            "employee_name": emp_name,
            "start": from_t.isoformat() if from_t else None,
            "end": (a.to_time or now).isoformat(),
            "progress": 100 if a.to_time else 50,
        })

        t = totals_by_emp[a.employee_id]
        t["employee_name"] = emp_name
        t["assignments"] += 1
        t["gross_seconds"] += gross
        t["net_seconds"] += net
        if a.work_run_id:
            t["work_runs"].add(a.work_run_id)

    employee_totals = []
    for emp_id, t in totals_by_emp.items():
        employee_totals.append({
            "employee_id": emp_id,
            "employee_name": t["employee_name"],
            "assignments": t["assignments"],
            "work_runs": len(t["work_runs"]),
            "gross_hours": round(t["gross_seconds"] / 3600.0, 2),
            "net_hours": round(t["net_seconds"] / 3600.0, 2),
        })
    employee_totals.sort(key=lambda d: -d["net_hours"])

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "assignments_count": len(rows),
        "unique_employees": len({r["employee_id"] for r in rows}),
        "total_gross_hours": round(sum(r["gross_hours"] for r in rows), 2),
        "total_net_hours": round(sum(r["net_hours"] for r in rows), 2),
        "open_assignments": sum(1 for r in rows if r["open"]),
    }
    by_day_hours = [
        {"day": day, "net_hours": round(secs / 3600.0, 2)}
        for day, secs in net_seconds_by_day.items()
    ]
    by_day_hours.sort(key=lambda d: d["day"])

    breakdown = {"by_day_hours": by_day_hours}
    return {"summary": summary, "rows": rows, "gantt": gantt, "employee_totals": employee_totals, "breakdown": breakdown}


def _empty_summary(params):
    return {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "assignments_count": 0,
        "unique_employees": 0,
        "total_gross_hours": 0,
        "total_net_hours": 0,
        "open_assignments": 0,
    }
