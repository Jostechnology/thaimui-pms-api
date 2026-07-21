"""Testing cost report — TestResultCost per TestResult."""

from app.app import db
from app.con_sqlalchemy import (
    QCWorkOrder, SalesItem, TestResult, TestResultCost,
    TestResultStatus, TestSessionStatus, TestType,
)
from app.reports._filters import parse_enum_list
from app.utils import convert_start_date, convert_end_date


def _z(v): return float(v) if v is not None else 0.0


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    overall_statuses = parse_enum_list(params.get("overall_status"), TestResultStatus, "overall_status")
    session_statuses = parse_enum_list(params.get("session_status"), TestSessionStatus, "session_status")
    test_types = parse_enum_list(params.get("test_type"), TestType, "test_type")

    q = (
        db.session.query(TestResult, TestResultCost, QCWorkOrder, SalesItem)
        .outerjoin(TestResultCost, TestResultCost.test_result_id == TestResult.test_result_id)
        .outerjoin(QCWorkOrder, QCWorkOrder.qc_work_order_id == TestResult.qc_work_order_id)
        .outerjoin(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
        .filter(TestResult.created_date >= start, TestResult.created_date <= end)
    )
    if overall_statuses:
        q = q.filter(TestResult.overall_status.in_(overall_statuses))
    if session_statuses:
        q = q.filter(TestResult.session_status.in_(session_statuses))
    if test_types:
        q = q.filter(TestResult.test_type.in_(test_types))
    q = q.order_by(TestResult.test_result_id.desc())

    rows = []
    totals = {"material": 0.0, "machine": 0.0, "labor": 0.0, "total": 0.0}
    total_claimed = 0

    for tr, cost, qc, si in q.all():
        mat = _z(cost.material_cost if cost else 0)
        machine = _z(cost.depreciation_cost if cost else 0) + _z(cost.maintenance_cost if cost else 0)
        labor = _z(cost.base_labor_cost if cost else 0) + _z(cost.day_labor_cost if cost else 0) + _z(cost.ot_labor_cost if cost else 0)
        total = _z(cost.total_cost if cost else 0) or (mat + machine + labor)
        claimed = tr.claimed_qty or 0

        rows.append({
            "test_result_id": tr.test_result_id,
            "test_result_code": tr.test_result_code,
            "qc_work_order_code": qc.qc_work_order_code if qc else None,
            "item_code": si.item_code if si else None,
            "item_name": si.item_name if si else None,
            "session_status": tr.session_status.value if tr.session_status else None,
            "overall_status": tr.overall_status.value if tr.overall_status else None,
            "claimed_qty": claimed,
            "material_cost": round(mat, 2),
            "machine_cost": round(machine, 2),
            "labor_cost": round(labor, 2),
            "total_cost": round(total, 2),
            "unit_cost": round(total / claimed, 2) if claimed > 0 else None,
            "started_at": tr.started_at.isoformat() if tr.started_at else None,
        })
        totals["material"] += mat
        totals["machine"] += machine
        totals["labor"] += labor
        totals["total"] += total
        total_claimed += claimed

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "test_result_count": len(rows),
        "total_claimed_qty": total_claimed,
        "total_material_cost": round(totals["material"], 2),
        "total_machine_cost": round(totals["machine"], 2),
        "total_labor_cost": round(totals["labor"], 2),
        "total_cost": round(totals["total"], 2),
        "avg_unit_cost": round(totals["total"] / total_claimed, 2) if total_claimed > 0 else 0,
    }

    status_counts = {}
    for r in rows:
        key = r["overall_status"] or "-"
        status_counts[key] = status_counts.get(key, 0) + 1
    by_status = [{"status": status, "count": count} for status, count in status_counts.items()]

    day_totals = {}
    for r in rows:
        if not r["started_at"]:
            continue
        day = r["started_at"][:10]
        day_totals[day] = day_totals.get(day, 0.0) + r["total_cost"]
    by_day = [
        {"day": day, "total_cost": round(total, 2)}
        for day, total in sorted(day_totals.items())
    ]

    # Cost-efficiency scatter over the FULL row set: tested qty vs unit cost.
    cost_scatter = [
        {
            "name": r["test_result_code"] or f"#{r['test_result_id']}",
            "qty": r["claimed_qty"],
            "unit_cost": r["unit_cost"],
        }
        for r in rows
        if (r["claimed_qty"] or 0) > 0
    ]

    breakdown = {
        "cost_mix": [
            {"name": "วัตถุดิบ", "value": summary["total_material_cost"]},
            {"name": "เครื่อง", "value": summary["total_machine_cost"]},
            {"name": "ค่าแรง", "value": summary["total_labor_cost"]},
        ],
        "by_status": by_status,
        "by_day": by_day,
        "cost_scatter": cost_scatter,
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
