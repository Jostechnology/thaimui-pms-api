"""Machine utilization — sum used hours per machine across WorkRunMachine + TestResultMachine."""

from collections import defaultdict
from datetime import datetime, timedelta

from app.app import db
from app.con_sqlalchemy import Machine, MachineStatus, TestResultMachine, WorkRunMachine
from app.reports._filters import parse_enum_list, parse_int
from app.utils import convert_start_date, convert_end_date


def _overlap_seconds(a_start, a_end, p_start, p_end):
    if not a_start:
        return 0
    end = a_end or datetime.now()
    start = max(a_start, p_start)
    finish = min(end, p_end)
    if finish <= start:
        return 0
    return int((finish - start).total_seconds())


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    machine_id = parse_int(params.get("machine_id"))
    machine_type_id = parse_int(params.get("machine_type_id"))
    machine_statuses = parse_enum_list(params.get("machine_status"), MachineStatus, "machine_status")

    period_seconds = max(0, int((end - start).total_seconds()))
    period_days = period_seconds / 86400.0

    # `machines` is the authoritative filtered set — usage for machines outside
    # it is dropped below, so machine_type/status filters actually restrict rows.
    m_query = db.session.query(Machine)
    if machine_id:
        m_query = m_query.filter(Machine.machine_id == machine_id)
    if machine_type_id:
        m_query = m_query.filter(Machine.machine_type_id == machine_type_id)
    if machine_statuses:
        m_query = m_query.filter(Machine.status.in_(machine_statuses))
    machines = {m.machine_id: m for m in m_query.all()}

    wq = (
        db.session.query(WorkRunMachine)
        .filter(
            WorkRunMachine.from_time <= end,
            (WorkRunMachine.to_time.is_(None)) | (WorkRunMachine.to_time >= start),
        )
    )
    tq = (
        db.session.query(TestResultMachine)
        .filter(
            TestResultMachine.from_time <= end,
            (TestResultMachine.to_time.is_(None)) | (TestResultMachine.to_time >= start),
        )
    )

    used_by_machine = defaultdict(lambda: {"workrun_seconds": 0, "test_seconds": 0})

    for wrm in wq.all():
        if wrm.machine_id not in machines:
            continue
        used_by_machine[wrm.machine_id]["workrun_seconds"] += _overlap_seconds(
            wrm.from_time, wrm.to_time, start, end
        )

    for trm in tq.all():
        if trm.machine_id not in machines:
            continue
        used_by_machine[trm.machine_id]["test_seconds"] += _overlap_seconds(
            trm.from_time, trm.to_time, start, end
        )

    rows = []
    total_used = 0
    total_available = 0
    for mid, used in used_by_machine.items():
        m = machines.get(mid)
        if m is None:
            # outside the filtered machine set — skip.
            continue
        whpd = (m.working_hours_per_day if m and m.working_hours_per_day else 0) or 0
        available_hours = round(whpd * period_days, 2)
        used_hours = round((used["workrun_seconds"] + used["test_seconds"]) / 3600.0, 2)
        util_pct = round((used_hours / available_hours) * 100, 2) if available_hours > 0 else 0
        rows.append({
            "machine_id": mid,
            "machine_code": m.machine_code if m else None,
            "machine_name": m.machine_name if m else None,
            "machine_type": m.machine_type.type_name if (m and m.machine_type) else None,
            "working_hours_per_day": whpd,
            "available_hours": available_hours,
            "workrun_hours": round(used["workrun_seconds"] / 3600.0, 2),
            "test_hours": round(used["test_seconds"] / 3600.0, 2),
            "used_hours": used_hours,
            "utilization_pct": util_pct,
        })
        total_used += used_hours
        total_available += available_hours

    # Include machines with zero usage if a single machine filter is given
    if machine_id and machine_id not in used_by_machine and machine_id in machines:
        m = machines[machine_id]
        whpd = m.working_hours_per_day or 0
        available_hours = round(whpd * period_days, 2)
        rows.append({
            "machine_id": machine_id, "machine_code": m.machine_code, "machine_name": m.machine_name,
            "machine_type": None,
            "working_hours_per_day": whpd, "available_hours": available_hours,
            "workrun_hours": 0, "test_hours": 0, "used_hours": 0,
            "utilization_pct": 0,
        })
        total_available += available_hours

    rows.sort(key=lambda r: -r["utilization_pct"])

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "machine_count": len(rows),
        "total_used_hours": round(total_used, 2),
        "total_available_hours": round(total_available, 2),
        "fleet_utilization_pct": round((total_used / total_available) * 100, 2) if total_available > 0 else 0,
    }

    breakdown = {
        "util_ranked": [
            {
                "machine_code": r["machine_code"] or ("M#" + str(r["machine_id"])),
                "utilization_pct": r["utilization_pct"],
            }
            for r in sorted(rows, key=lambda r: -r["utilization_pct"])[:15]
        ],
        "used_vs_available": [
            {
                "machine_code": r["machine_code"] or ("M#" + str(r["machine_id"])),
                "used_hours": r["used_hours"],
                "available_hours": r["available_hours"],
            }
            for r in sorted(rows, key=lambda r: -r["used_hours"])[:15]
        ],
        "fleet_split": [
            {"name": "ใช้งาน", "value": summary["total_used_hours"]},
            {"name": "ว่าง", "value": round(max(0, summary["total_available_hours"] - summary["total_used_hours"]), 2)},
        ],
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
