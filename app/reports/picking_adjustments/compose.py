"""Picking adjustments report."""

from collections import defaultdict

from app.app import db
from app.con_sqlalchemy import (
    PickingItemAdjustment, PickingItemAdjustmentReason, PickingRequest, PickingRequestItem,
)
from app.exception import ValidationError
from app.utils import convert_start_date, convert_end_date


def _parse_reasons(raw):
    """Accept a single reason or a comma-separated list. Returns a list of
    enums (for `.in_()`) or None when empty."""
    if not raw:
        return None
    values = [v.strip() for v in str(raw).split(",") if v.strip()]
    result = []
    for v in values:
        try:
            result.append(PickingItemAdjustmentReason[v.upper()])
        except KeyError:
            allowed = [r.value for r in PickingItemAdjustmentReason]
            raise ValidationError(f"reason ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")
    return result or None


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    reasons = _parse_reasons(params.get("reason"))

    q = (
        db.session.query(PickingItemAdjustment, PickingRequestItem, PickingRequest)
        .join(PickingRequestItem, PickingRequestItem.picking_request_item_id == PickingItemAdjustment.picking_request_item_id)
        .outerjoin(PickingRequest, PickingRequest.picking_request_id == PickingRequestItem.picking_request_id)
        .filter(PickingItemAdjustment.created_date >= start, PickingItemAdjustment.created_date <= end)
    )
    if reasons is not None:
        q = q.filter(PickingItemAdjustment.reason.in_(reasons))
    q = q.order_by(PickingItemAdjustment.id.desc())

    rows = []
    by_reason = defaultdict(lambda: {"count": 0, "delta_sum": 0})
    total_delta = 0

    for adj, pri, pr in q.all():
        rows.append({
            "adjustment_id": adj.id,
            "picking_request_code": pr.picking_request_code if pr else None,
            "picking_request_item_id": adj.picking_request_item_id,
            "item_code": pri.item_code if pri else None,
            "item_name": pri.item_name if pri else None,
            "delta_qty": adj.delta_qty,
            "reason": adj.reason.value if adj.reason else None,
            "remark": adj.remark,
            "created_by": adj.created_by,
            "created_date": adj.created_date.isoformat() if adj.created_date else None,
        })
        r = adj.reason.value if adj.reason else "UNKNOWN"
        by_reason[r]["count"] += 1
        by_reason[r]["delta_sum"] += adj.delta_qty or 0
        total_delta += adj.delta_qty or 0

    reason_breakdown = [
        {"reason": k, "count": v["count"], "delta_sum": v["delta_sum"]}
        for k, v in by_reason.items()
    ]
    reason_breakdown.sort(key=lambda d: -d["count"])

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "adjustments_count": len(rows),
        "total_delta_qty": total_delta,
        "miscount": by_reason.get("MISCOUNT", {}).get("count", 0),
        "spillage": by_reason.get("SPILLAGE", {}).get("count", 0),
        "correction": by_reason.get("CORRECTION", {}).get("count", 0),
        "reallocate": by_reason.get("REALLOCATE", {}).get("count", 0),
        "other": by_reason.get("OTHER", {}).get("count", 0),
    }
    breakdown_by_reason = [
        {"reason": d["reason"], "count": d["count"], "delta_sum": d["delta_sum"]}
        for d in reason_breakdown
    ]

    by_day_map = defaultdict(lambda: {"count": 0, "delta_sum": 0})
    for r in rows:
        if not r["created_date"]:
            continue
        day = r["created_date"][:10]
        by_day_map[day]["count"] += 1
        by_day_map[day]["delta_sum"] += r["delta_qty"] or 0
    by_day = [
        {"day": day, "count": v["count"], "delta_sum": v["delta_sum"]}
        for day, v in by_day_map.items()
    ]
    by_day.sort(key=lambda d: d["day"])

    breakdown = {"by_reason": breakdown_by_reason, "by_day": by_day}
    return {"summary": summary, "rows": rows, "reason_breakdown": reason_breakdown, "breakdown": breakdown}
