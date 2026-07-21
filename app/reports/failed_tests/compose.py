"""Failed tests report."""

from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import (
    QCWorkOrder, SalesItem, TestResult, TestResultItem, TestResultStatus,
    TestSessionStatus, TestType,
)
from app.reports._filters import parse_enum_list
from app.utils import convert_start_date, convert_end_date


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    session_statuses = parse_enum_list(params.get("session_status"), TestSessionStatus, "session_status")
    test_types = parse_enum_list(params.get("test_type"), TestType, "test_type")

    q = (
        db.session.query(TestResult, QCWorkOrder, SalesItem)
        .options(selectinload(TestResult.test_result_items))
        .outerjoin(QCWorkOrder, QCWorkOrder.qc_work_order_id == TestResult.qc_work_order_id)
        .outerjoin(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
        .filter(
            TestResult.created_date >= start,
            TestResult.created_date <= end,
            TestResult.overall_status == TestResultStatus.FAILED,
        )
    )
    if session_statuses:
        q = q.filter(TestResult.session_status.in_(session_statuses))
    if test_types:
        q = q.filter(TestResult.test_type.in_(test_types))
    q = q.order_by(TestResult.test_result_id.desc())

    rows = []
    total_claimed = 0
    total_failed_items = 0

    for tr, qc, si in q.all():
        items = tr.test_result_items or []
        failed_units = sum(1 for it in items if it.result == TestResultStatus.FAILED)
        sample_failed_units = ", ".join(
            str(it.unit_number) for it in items if it.result == TestResultStatus.FAILED
        )[:255]
        rows.append({
            "test_result_id": tr.test_result_id,
            "test_result_code": tr.test_result_code,
            "qc_work_order_code": qc.qc_work_order_code if qc else None,
            "item_code": si.item_code if si else None,
            "item_name": si.item_name if si else None,
            "claimed_qty": tr.claimed_qty,
            "failed_qty": failed_units,
            "passed_qty": (tr.claimed_qty or 0) - failed_units,
            "failed_units": sample_failed_units,
            "started_at": tr.started_at.isoformat() if tr.started_at else None,
            "remark": tr.remark,
        })
        total_claimed += tr.claimed_qty or 0
        total_failed_items += failed_units

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "failed_tests": len(rows),
        "total_claimed_qty": total_claimed,
        "total_failed_items": total_failed_items,
        "fail_rate_pct": round((total_failed_items / total_claimed) * 100, 2) if total_claimed > 0 else 0,
    }

    by_item = [
        {
            "item_code": r["item_code"],
            "failed_qty": r["failed_qty"],
            "claimed_qty": r["claimed_qty"],
        }
        for r in sorted(rows, key=lambda r: r["failed_qty"], reverse=True)[:15]
    ]

    day_totals = {}
    for r in rows:
        if not r["started_at"]:
            continue
        day = r["started_at"][:10]
        agg = day_totals.setdefault(day, {"failed_qty": 0, "claimed_qty": 0})
        agg["failed_qty"] += r["failed_qty"] or 0
        agg["claimed_qty"] += r["claimed_qty"] or 0
    by_day = [
        {"day": day, "failed_qty": agg["failed_qty"], "claimed_qty": agg["claimed_qty"]}
        for day, agg in sorted(day_totals.items())
    ]

    breakdown = {
        "pass_fail": [
            {"name": "ผ่าน", "value": summary["total_claimed_qty"] - summary["total_failed_items"]},
            {"name": "ไม่ผ่าน", "value": summary["total_failed_items"]},
        ],
        "by_item": by_item,
        "by_day": by_day,
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
