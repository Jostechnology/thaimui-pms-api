"""SO cycle time — days from created to COMPLETED (or to today if still open)."""

from collections import defaultdict
from datetime import datetime

from app.app import db
from app.con_sqlalchemy import SalesOrder, SalesOrderStatus, UrgencyLevel
from app.exception import ValidationError
from app.reports._filters import parse_enum_list
from app.utils import convert_start_date, convert_end_date

_CYCLE_BUCKETS = ["0-1", "1-3", "3-7", "7-14", "14-30", "30+"]


def _cycle_bucket(days):
    if days < 1:
        return "0-1"
    if days < 3:
        return "1-3"
    if days < 7:
        return "3-7"
    if days < 14:
        return "7-14"
    if days < 30:
        return "14-30"
    return "30+"


def _parse_statuses(raw):
    """Accept a single status or a comma-separated list. Returns a list of
    enums (for `.in_()`) or None when empty."""
    if not raw:
        return None
    values = [v.strip() for v in str(raw).split(",") if v.strip()]
    result = []
    for v in values:
        try:
            result.append(SalesOrderStatus[v.upper()])
        except KeyError:
            allowed = [s.value for s in SalesOrderStatus]
            raise ValidationError(f"status ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")
    return result or None


def compose(params):
    start = convert_start_date(params["from"])
    end = convert_end_date(params["to"])
    statuses = _parse_statuses(params.get("status"))
    urgencies = parse_enum_list(params.get("urgency_level"), UrgencyLevel, "urgency_level")

    q = db.session.query(SalesOrder).filter(
        SalesOrder.created_date >= start, SalesOrder.created_date <= end,
    )
    if statuses is not None:
        q = q.filter(SalesOrder.status.in_(statuses))
    if urgencies is not None:
        q = q.filter(SalesOrder.urgency_level.in_(urgencies))
    q = q.order_by(SalesOrder.created_date.desc())

    now = datetime.now()
    rows = []
    completed_days_list = []
    open_days_list = []

    for so in q.all():
        created = so.created_date
        is_completed = so.status == SalesOrderStatus.COMPLETED
        end_ref = (so.updated_date or created) if is_completed else now
        days = round(((end_ref - created).total_seconds() / 86400.0), 2) if created and end_ref else None
        rows.append({
            "doc_entry": so.doc_entry,
            "doc_num": so.doc_num,
            "card_code": so.card_code,
            "card_name": so.card_name,
            "urgency_level": so.urgency_level.value if so.urgency_level else None,
            "status": so.status.value,
            "created_date": created.isoformat() if created else None,
            "completed_date": so.updated_date.isoformat() if (is_completed and so.updated_date) else None,
            "days_elapsed": days,
        })
        if days is None:
            continue
        if is_completed:
            completed_days_list.append(days)
        else:
            open_days_list.append(days)

    summary = {
        "period_from": params.get("from"),
        "period_to": params.get("to"),
        "total_orders": len(rows),
        "completed_orders": len(completed_days_list),
        "open_orders": len(open_days_list),
        "avg_days_to_complete": round(sum(completed_days_list) / len(completed_days_list), 2) if completed_days_list else 0,
        "max_days_to_complete": round(max(completed_days_list), 2) if completed_days_list else 0,
        "avg_days_open": round(sum(open_days_list) / len(open_days_list), 2) if open_days_list else 0,
        "max_days_open": round(max(open_days_list), 2) if open_days_list else 0,
    }

    status_days = defaultdict(list)
    status_count = defaultdict(int)
    urgency_count = defaultdict(int)
    bucket_count = defaultdict(int)
    for r in rows:
        status_count[r["status"]] += 1
        if r["days_elapsed"] is not None:
            status_days[r["status"]].append(r["days_elapsed"])
            bucket_count[_cycle_bucket(r["days_elapsed"])] += 1
        urgency_count[r["urgency_level"] or "ไม่ระบุ"] += 1

    breakdown = {
        "by_status": [
            {
                "status": s,
                "count": status_count[s],
                "avg_days": round(sum(status_days[s]) / len(status_days[s]), 2) if status_days[s] else 0,
            }
            for s in status_count
        ],
        "by_urgency": [
            {"urgency_level": u, "count": c}
            for u, c in urgency_count.items()
        ],
        "cycle_distribution": [
            {"bucket": b, "count": bucket_count[b]}
            for b in _CYCLE_BUCKETS
        ],
    }
    return {"summary": summary, "rows": rows, "breakdown": breakdown}
