"""Material consumption report — aggregate PRI consumption across WorkRun + TestResult."""

from collections import defaultdict

from sqlalchemy import case, func

from app.app import db
from app.con_sqlalchemy import (
    PickingRequestItem, TestResult, TestResultPickingItem,
    WorkRun, WorkRunPickingItem,
)
from app.utils import convert_start_date, convert_end_date


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])

    # WorkRun side — qty_consumed if not null else qty_allocated; filter by WorkRun.created_date
    consumed_w = case(
        (WorkRunPickingItem.qty_consumed.isnot(None), WorkRunPickingItem.qty_consumed),
        else_=WorkRunPickingItem.qty_allocated,
    )
    wq = (
        db.session.query(
            PickingRequestItem.item_code.label("item_code"),
            PickingRequestItem.item_name.label("item_name"),
            PickingRequestItem.unit.label("unit"),
            func.coalesce(func.sum(consumed_w), 0).label("qty"),
        )
        .join(PickingRequestItem, PickingRequestItem.picking_request_item_id == WorkRunPickingItem.picking_request_item_id)
        .join(WorkRun, WorkRun.work_run_id == WorkRunPickingItem.work_run_id)
        .filter(WorkRun.created_date >= start, WorkRun.created_date <= end)
        .group_by(PickingRequestItem.item_code, PickingRequestItem.item_name, PickingRequestItem.unit)
    )

    # TestResult side
    consumed_t = case(
        (TestResultPickingItem.qty_consumed.isnot(None), TestResultPickingItem.qty_consumed),
        else_=TestResultPickingItem.qty_allocated,
    )
    tq = (
        db.session.query(
            PickingRequestItem.item_code.label("item_code"),
            PickingRequestItem.item_name.label("item_name"),
            PickingRequestItem.unit.label("unit"),
            func.coalesce(func.sum(consumed_t), 0).label("qty"),
        )
        .join(PickingRequestItem, PickingRequestItem.picking_request_item_id == TestResultPickingItem.picking_request_item_id)
        .join(TestResult, TestResult.test_result_id == TestResultPickingItem.test_result_id)
        .filter(TestResult.created_date >= start, TestResult.created_date <= end)
        .group_by(PickingRequestItem.item_code, PickingRequestItem.item_name, PickingRequestItem.unit)
    )

    agg = defaultdict(lambda: {"item_name": None, "unit": None, "qty_workrun": 0, "qty_testresult": 0})
    for row in wq.all():
        key = row.item_code
        agg[key]["item_name"] = row.item_name
        agg[key]["unit"] = row.unit
        agg[key]["qty_workrun"] += int(row.qty or 0)
    for row in tq.all():
        key = row.item_code
        agg[key]["item_name"] = agg[key]["item_name"] or row.item_name
        agg[key]["unit"] = agg[key]["unit"] or row.unit
        agg[key]["qty_testresult"] += int(row.qty or 0)

    rows = []
    total_w = total_t = 0
    for code, v in agg.items():
        total_qty = v["qty_workrun"] + v["qty_testresult"]
        rows.append({
            "item_code": code,
            "item_name": v["item_name"],
            "unit": v["unit"],
            "qty_workrun": v["qty_workrun"],
            "qty_testresult": v["qty_testresult"],
            "total_qty": total_qty,
        })
        total_w += v["qty_workrun"]
        total_t += v["qty_testresult"]

    rows.sort(key=lambda r: -r["total_qty"])

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "unique_items": len(rows),
        "total_qty_workrun": total_w,
        "total_qty_testresult": total_t,
        "total_qty": total_w + total_t,
    }

    breakdown = {
        "by_item": [
            {"item_code": r["item_code"], "total_qty": r["total_qty"]}
            for r in sorted(rows, key=lambda r: -r["total_qty"])[:15]
        ],
        "source_split": [
            {"name": "WorkRun", "value": summary["total_qty_workrun"]},
            {"name": "TestResult", "value": summary["total_qty_testresult"]},
        ],
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
