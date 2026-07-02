"""Production cost report — WorkRunCost rolled up per WorkRun."""

from sqlalchemy.orm import joinedload

from app.app import db
from app.con_sqlalchemy import WorkRun, WorkRunCost, WorkOrder, SalesItem
from app.utils import convert_start_date, convert_end_date


def _cost_or_zero(v):
    return float(v) if v is not None else 0.0


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    work_order_id = params.get("work_order_id")

    q = (
        db.session.query(WorkRun, WorkRunCost, WorkOrder, SalesItem)
        .outerjoin(WorkRunCost, WorkRunCost.work_run_id == WorkRun.work_run_id)
        .outerjoin(WorkOrder, WorkOrder.work_order_id == WorkRun.work_order_id)
        .outerjoin(SalesItem, SalesItem.sales_item_id == WorkOrder.sales_item_id)
        .filter(WorkRun.created_date >= start, WorkRun.created_date <= end)
    )
    if work_order_id:
        q = q.filter(WorkRun.work_order_id == work_order_id)
    q = q.order_by(WorkRun.work_run_id.desc())

    rows = []
    totals = {"material": 0.0, "depr": 0.0, "maint": 0.0, "base": 0.0, "day": 0.0, "ot": 0.0, "total": 0.0}
    total_planned_qty = 0
    total_usable_qty = 0

    for wr, cost, wo, si in q.all():
        mat = _cost_or_zero(cost.material_cost if cost else 0)
        depr = _cost_or_zero(cost.depreciation_cost if cost else 0)
        maint = _cost_or_zero(cost.maintenance_cost if cost else 0)
        base = _cost_or_zero(cost.base_labor_cost if cost else 0)
        day = _cost_or_zero(cost.day_labor_cost if cost else 0)
        ot = _cost_or_zero(cost.ot_labor_cost if cost else 0)
        total = _cost_or_zero(cost.total_cost if cost else 0) or (mat + depr + maint + base + day + ot)
        machine_cost = depr + maint
        labor_cost = base + day + ot
        usable = wr.usable_qty
        unit_cost = round(total / usable, 2) if usable and usable > 0 else None

        rows.append({
            "work_run_id": wr.work_run_id,
            "lot_number": wr.lot_number,
            "work_order_id": wr.work_order_id,
            "item_code": si.item_code if si else None,
            "item_name": si.item_name if si else None,
            "status": wr.status.value,
            "planned_qty": wr.quantity,
            "usable_qty": usable,
            "material_cost": round(mat, 2),
            "machine_cost": round(machine_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "total_cost": round(total, 2),
            "unit_cost": unit_cost,
            "completed_date": wr.end_date.isoformat() if wr.end_date else None,
        })
        totals["material"] += mat
        totals["depr"] += depr
        totals["maint"] += maint
        totals["base"] += base
        totals["day"] += day
        totals["ot"] += ot
        totals["total"] += total
        total_planned_qty += wr.quantity or 0
        total_usable_qty += usable or 0

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "workrun_count": len(rows),
        "total_planned_qty": total_planned_qty,
        "total_usable_qty": total_usable_qty,
        "total_material_cost": round(totals["material"], 2),
        "total_machine_cost": round(totals["depr"] + totals["maint"], 2),
        "total_labor_cost": round(totals["base"] + totals["day"] + totals["ot"], 2),
        "total_cost": round(totals["total"], 2),
        "avg_unit_cost": round(totals["total"] / total_usable_qty, 2) if total_usable_qty > 0 else 0,
    }

    by_workrun = [
        {
            "label": r["lot_number"] or f"WR#{r['work_run_id']}",
            "total_cost": r["total_cost"],
        }
        for r in sorted(rows, key=lambda r: r["total_cost"], reverse=True)[:15]
    ]

    day_totals = {}
    for r in rows:
        if not r["completed_date"]:
            continue
        day = r["completed_date"][:10]
        day_totals[day] = day_totals.get(day, 0.0) + r["total_cost"]
    by_day = [
        {"day": day, "total_cost": round(total, 2)}
        for day, total in sorted(day_totals.items())
    ]

    # Cost-efficiency scatter over the FULL row set: produced qty vs unit cost.
    cost_scatter = [
        {
            "name": r["lot_number"] or f"WR#{r['work_run_id']}",
            "qty": r["usable_qty"],
            "unit_cost": r["unit_cost"],
        }
        for r in rows
        if (r["usable_qty"] or 0) > 0
    ]

    breakdown = {
        "cost_mix": [
            {"name": "วัตถุดิบ", "value": summary["total_material_cost"]},
            {"name": "เครื่องจักร", "value": summary["total_machine_cost"]},
            {"name": "ค่าแรง", "value": summary["total_labor_cost"]},
        ],
        "by_workrun": by_workrun,
        "by_day": by_day,
        "cost_scatter": cost_scatter,
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
