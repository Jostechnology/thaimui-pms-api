"""WorkRun defects report."""

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.app import db
from app.con_sqlalchemy import (
    SalesItem, WorkOrder, WorkRun, WorkRunReworkSource, WorkRunStatus,
)
from app.utils import convert_start_date, convert_end_date


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])

    # Sub: how much of this WR's defect has been consumed by rework runs
    consumed_subq = (
        db.session.query(
            WorkRunReworkSource.source_work_run_id.label("wr_id"),
            func.coalesce(func.sum(WorkRunReworkSource.qty), 0).label("consumed"),
        )
        .group_by(WorkRunReworkSource.source_work_run_id)
        .subquery()
    )

    q = (
        db.session.query(WorkRun, WorkOrder, SalesItem, consumed_subq.c.consumed)
        .outerjoin(consumed_subq, consumed_subq.c.wr_id == WorkRun.work_run_id)
        .outerjoin(WorkOrder, WorkOrder.work_order_id == WorkRun.work_order_id)
        .outerjoin(SalesItem, SalesItem.sales_item_id == WorkOrder.sales_item_id)
        .filter(
            WorkRun.created_date >= start,
            WorkRun.created_date <= end,
            WorkRun.status == WorkRunStatus.COMPLETED,
            WorkRun.usable_qty.isnot(None),
            WorkRun.usable_qty < WorkRun.quantity,
        )
        .order_by(WorkRun.work_run_id.desc())
    )

    rows = []
    total_planned = 0
    total_usable = 0
    total_defect = 0
    total_outstanding = 0
    runs_with_rework = 0

    for wr, wo, si, consumed in q.all():
        planned = wr.quantity or 0
        usable = wr.usable_qty or 0
        defect = planned - usable
        consumed = int(consumed or 0)
        outstanding = max(0, defect - consumed)
        has_rework = consumed > 0
        if has_rework:
            runs_with_rework += 1
        rows.append({
            "work_run_id": wr.work_run_id,
            "lot_number": wr.lot_number,
            "work_order_id": wr.work_order_id,
            "item_code": si.item_code if si else None,
            "item_name": si.item_name if si else None,
            "planned_qty": planned,
            "usable_qty": usable,
            "defect_qty": defect,
            "consumed_defect_qty": consumed,
            "outstanding_defect_qty": outstanding,
            "has_rework": has_rework,
            "defect_rate_pct": round((defect / planned) * 100, 2) if planned > 0 else 0,
            "completed_date": wr.end_date.isoformat() if wr.end_date else None,
            "remark": wr.completion_remark,
        })
        total_planned += planned
        total_usable += usable
        total_defect += defect
        total_outstanding += outstanding

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "workrun_count": len(rows),
        "total_planned_qty": total_planned,
        "total_usable_qty": total_usable,
        "total_defect_qty": total_defect,
        "total_outstanding_defect_qty": total_outstanding,
        "runs_with_rework": runs_with_rework,
        "defect_rate_pct": round((total_defect / total_planned) * 100, 2) if total_planned > 0 else 0,
    }

    by_item = [
        {
            "label": r["lot_number"] or f"WR#{r['work_run_id']}",
            "defect_qty": r["defect_qty"],
        }
        for r in sorted(rows, key=lambda r: r["defect_qty"], reverse=True)[:15]
    ]

    day_totals = {}
    for r in rows:
        if not r["completed_date"]:
            continue
        day = r["completed_date"][:10]
        day_totals[day] = day_totals.get(day, 0) + (r["defect_qty"] or 0)
    by_day = [
        {"day": day, "defect_qty": defect_qty}
        for day, defect_qty in sorted(day_totals.items())
    ]

    breakdown = {
        "rework_split": [
            {"name": "Rework แล้ว", "value": sum(r["consumed_defect_qty"] for r in rows)},
            {"name": "คงค้าง", "value": sum(r["outstanding_defect_qty"] for r in rows)},
        ],
        "by_item": by_item,
        "by_day": by_day,
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
