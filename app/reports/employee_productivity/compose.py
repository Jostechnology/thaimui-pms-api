"""Employee productivity — attribute usable_qty per worker by hours-on-run."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.app import db
from app.con_sqlalchemy import Employee, WorkRun, WorkRunAssignment, WorkRunStatus
from app.reports._filters import parse_int
from app.utils import convert_start_date, convert_end_date


def _hours_between(a, b):
    if not a or not b:
        return 0.0
    return max(0.0, (b - a).total_seconds() / 3600.0)


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    employee_id = parse_int(params.get("employee_id"))
    work_order_id = parse_int(params.get("work_order_id"))

    # All assignments in window
    a_query = (
        db.session.query(WorkRunAssignment)
        .options(joinedload(WorkRunAssignment.employee), joinedload(WorkRunAssignment.work_run))
        .filter(WorkRunAssignment.from_time >= start, WorkRunAssignment.from_time <= end)
    )
    if employee_id:
        a_query = a_query.filter(WorkRunAssignment.employee_id == employee_id)
    if work_order_id:
        a_query = a_query.filter(WorkRunAssignment.work_run.has(WorkRun.work_order_id == work_order_id))
    assignments = a_query.all()

    # Group hours per (work_run, employee) + per work_run total hours
    hours_emp_run = defaultdict(float)  # (work_run_id, emp_id) -> hours
    hours_per_run = defaultdict(float)  # work_run_id -> total hours
    emp_meta = {}
    run_to_assignments = defaultdict(int)
    now = datetime.now()

    for a in assignments:
        emp = a.employee
        if emp:
            emp_meta[a.employee_id] = f"{emp.employee_first_name} {emp.employee_last_name}"
        end_t = a.to_time or now
        hrs = _hours_between(a.from_time, end_t)
        hours_emp_run[(a.work_run_id, a.employee_id)] += hrs
        hours_per_run[a.work_run_id] += hrs
        run_to_assignments[a.employee_id] += 1

    # Fetch the WorkRuns involved (only COMPLETED with usable_qty contribute to attribution)
    run_ids = list({wid for (wid, _) in hours_emp_run.keys() if wid is not None})
    runs = {}
    if run_ids:
        for wr in db.session.query(WorkRun).filter(WorkRun.work_run_id.in_(run_ids)).all():
            runs[wr.work_run_id] = wr

    per_emp = defaultdict(lambda: {
        "employee_name": None,
        "assignments": 0,
        "work_runs": set(),
        "hours": 0.0,
        "attributed_usable": 0.0,
        "attributed_defect": 0.0,
    })

    for (wr_id, emp_id), hrs in hours_emp_run.items():
        bucket = per_emp[emp_id]
        bucket["employee_name"] = emp_meta.get(emp_id)
        bucket["hours"] += hrs
        if wr_id is not None:
            bucket["work_runs"].add(wr_id)
        wr = runs.get(wr_id)
        if wr and wr.status == WorkRunStatus.COMPLETED and wr.usable_qty is not None and hours_per_run[wr_id] > 0:
            share = hrs / hours_per_run[wr_id]
            bucket["attributed_usable"] += share * (wr.usable_qty or 0)
            defect = (wr.quantity or 0) - (wr.usable_qty or 0)
            bucket["attributed_defect"] += share * max(0, defect)

    rows = []
    for emp_id, b in per_emp.items():
        b["assignments"] = run_to_assignments.get(emp_id, 0)
        rows.append({
            "employee_id": emp_id,
            "employee_name": b["employee_name"],
            "assignments": b["assignments"],
            "work_runs": len(b["work_runs"]),
            "hours_worked": round(b["hours"], 2),
            "attributed_usable_qty": round(b["attributed_usable"], 2),
            "attributed_defect_qty": round(b["attributed_defect"], 2),
            "output_per_hour": round(b["attributed_usable"] / b["hours"], 2) if b["hours"] > 0 else 0,
        })
    rows.sort(key=lambda r: -r["attributed_usable_qty"])

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "employees": len(rows),
        "total_hours": round(sum(r["hours_worked"] for r in rows), 2),
        "total_usable_qty": round(sum(r["attributed_usable_qty"] for r in rows), 2),
        "total_defect_qty": round(sum(r["attributed_defect_qty"] for r in rows), 2),
    }

    by_employee = [
        {
            "employee_name": r["employee_name"],
            "attributed_usable_qty": r["attributed_usable_qty"],
            "hours_worked": r["hours_worked"],
            "output_per_hour": r["output_per_hour"],
        }
        for r in sorted(rows, key=lambda r: -r["attributed_usable_qty"])[:15]
    ]

    output_vs_hours = [
        {
            "name": r["employee_name"],
            "hours_worked": r["hours_worked"],
            "output_per_hour": r["output_per_hour"],
        }
        for r in rows if r["hours_worked"] > 0
    ]

    quality_split = [
        {"name": "ใช้ได้", "value": summary["total_usable_qty"]},
        {"name": "ของเสีย", "value": summary["total_defect_qty"]},
    ]

    breakdown = {
        "by_employee": by_employee,
        "output_vs_hours": output_vs_hours,
        "quality_split": quality_split,
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
