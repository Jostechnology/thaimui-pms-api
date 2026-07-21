"""Compose the picking-requests report payload."""

from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem, PickingRequestStatus, SalesOrder, UrgencyLevel,
)
from app.exception import ValidationError
from app.reports._filters import parse_enum_list
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
    urgencies = parse_enum_list(params.get("urgency_level"), UrgencyLevel, "urgency_level")

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
    if urgencies is not None:
        query = query.filter(SalesOrder.urgency_level.in_(urgencies))

    prs = query.order_by(PickingRequest.picking_request_id.desc()).all()

    rows = []
    status_counts = {s.value: 0 for s in PickingRequestStatus}
    total_items = 0
    total_qty_requested = 0

    for pr in prs:
        items = pr.items or []
        n_items = len(items)
        req_sum = sum(i.quantity for i in items)

        status_counts[pr.status.value] += 1
        total_items += n_items
        total_qty_requested += req_sum

        rows.append({
            "picking_request_id": pr.picking_request_id,
            "picking_request_code": pr.picking_request_code,
            "doc_num": pr.sales_order.doc_num if pr.sales_order else None,
            "status": pr.status.value,
            "wms_reference": pr.wms_reference,
            "items_count": n_items,
            "qty_requested": req_sum,
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
        bucket = by_day_map.setdefault(day, {"qty_requested": 0})
        bucket["qty_requested"] += r["qty_requested"]
    by_day = [
        {"day": day, "qty_requested": v["qty_requested"]}
        for day, v in by_day_map.items()
    ]
    by_day.sort(key=lambda d: d["day"])

    breakdown = {"by_status": by_status, "by_day": by_day}
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
