"""Compose the picking-requests report payload."""

from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem, PickingRequestStatus, SalesOrder,
)
from app.exception import ValidationError
from app.utils import convert_start_date, convert_end_date


def _parse_statuses(raw):
    """Accept a single status or a comma-separated list. Returns a list of
    enums (for `.in_()`) or None when empty."""
    if not raw:
        return None
    values = [v.strip() for v in str(raw).split(",") if v.strip()]
    result = []
    for v in values:
        try:
            result.append(PickingRequestStatus[v.upper()])
        except KeyError:
            allowed = [s.value for s in PickingRequestStatus]
            raise ValidationError(f"status ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")
    return result or None


def compose(params):
    start = convert_start_date(params["from"]) if params.get("from") else None
    end = convert_end_date(params["to"]) if params.get("to") else None
    statuses = _parse_statuses(params.get("status"))

    query = (
        db.session.query(PickingRequest)
        .outerjoin(SalesOrder, SalesOrder.doc_entry == PickingRequest.doc_entry)
        .options(
            selectinload(PickingRequest.items),
        )
    )
    if start is not None:
        query = query.filter(PickingRequest.created_date >= start)
    if end is not None:
        query = query.filter(PickingRequest.created_date <= end)
    if statuses is not None:
        query = query.filter(PickingRequest.status.in_(statuses))

    prs = query.order_by(PickingRequest.picking_request_id.desc()).all()

    rows = []
    status_counts = {s.value: 0 for s in PickingRequestStatus}
    total_items = 0
    total_qty_requested = 0
    total_qty_received = 0
    total_short_picks = 0  # items where received < requested

    for pr in prs:
        items = pr.items or []
        n_items = len(items)
        req_sum = sum(i.quantity for i in items)
        actual_sum = sum(
            (i.qty_received_actual if i.qty_received_actual is not None else i.quantity)
            for i in items
        )
        short = sum(
            1 for i in items
            if i.qty_received_actual is not None and i.qty_received_actual < i.quantity
        )
        delta = actual_sum - req_sum

        status_counts[pr.status.value] += 1
        total_items += n_items
        total_qty_requested += req_sum
        total_qty_received += actual_sum
        total_short_picks += short

        rows.append({
            "picking_request_id": pr.picking_request_id,
            "picking_request_code": pr.picking_request_code,
            "doc_num": pr.sales_order.doc_num if pr.sales_order else None,
            "status": pr.status.value,
            "wms_reference": pr.wms_reference,
            "is_reallocation": bool(pr.is_reallocation),
            "items_count": n_items,
            "qty_requested": req_sum,
            "qty_received": actual_sum,
            "qty_delta": delta,
            "short_picks": short,
            "created_by": pr.created_by,
            "created_date": pr.created_date.isoformat() if pr.created_date else None,
            "remark": pr.remark,
        })

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "total_requests": len(prs),
        "pending":  status_counts[PickingRequestStatus.PENDING.value],
        "sent":     status_counts[PickingRequestStatus.SENT.value],
        "success":  status_counts[PickingRequestStatus.SUCCESS.value],
        "failed":   status_counts[PickingRequestStatus.FAILED.value],
        "total_items": total_items,
        "total_qty_requested": total_qty_requested,
        "total_qty_received": total_qty_received,
        "total_qty_delta": total_qty_received - total_qty_requested,
        "short_pick_lines": total_short_picks,
    }

    by_status = [
        {"status": s.value, "count": status_counts[s.value]}
        for s in PickingRequestStatus
    ]

    by_day_map = {}
    for r in rows:
        if not r["created_date"]:
            continue
        day = r["created_date"][:10]
        bucket = by_day_map.setdefault(day, {"qty_requested": 0, "qty_received": 0})
        bucket["qty_requested"] += r["qty_requested"]
        bucket["qty_received"] += r["qty_received"]
    by_day = [
        {"day": day, "qty_requested": v["qty_requested"], "qty_received": v["qty_received"]}
        for day, v in by_day_map.items()
    ]
    by_day.sort(key=lambda d: d["day"])

    # Top SOs by absolute receive-vs-request delta (signed) for a diverging bar.
    delta_top = sorted(
        [
            {"name": r["doc_num"] or f"#{r['picking_request_id']}", "value": r["qty_delta"]}
            for r in rows
            if r["qty_delta"]
        ],
        key=lambda d: abs(d["value"]),
        reverse=True,
    )[:15]

    breakdown = {"by_status": by_status, "by_day": by_day, "delta_top": delta_top}
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
