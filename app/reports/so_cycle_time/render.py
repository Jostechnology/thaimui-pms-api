from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "doc_num",        "label": "เลข SO", "fmt": "int", "width": 12},
    {"field": "card_code",      "label": "รหัสลูกค้า", "width": 14},
    {"field": "card_name",      "label": "ลูกค้า", "width": 28},
    {"field": "urgency_level",  "label": "เร่งด่วน", "width": 12, "align": "center"},
    {"field": "status",         "label": "สถานะ", "width": 14, "align": "center"},
    {"field": "created_date",   "label": "สร้างเมื่อ", "fmt": "datetime", "width": 18},
    {"field": "completed_date", "label": "เสร็จเมื่อ", "fmt": "datetime", "width": 18},
    {"field": "days_elapsed",   "label": "วันที่ใช้", "fmt": "money1", "width": 12},
]

SUMMARY_LABELS = {
    "period_from":          "ตั้งแต่",
    "period_to":            "ถึง",
    "total_orders":         "จำนวน SO ทั้งหมด",
    "completed_orders":     "เสร็จสิ้น",
    "open_orders":          "ยังเปิดอยู่",
    "avg_days_to_complete": "เฉลี่ยวันที่เสร็จ",
    "max_days_to_complete": "สูงสุดวันที่เสร็จ",
    "avg_days_open":        "เฉลี่ยวันที่เปิดค้าง",
    "max_days_open":        "สูงสุดวันที่เปิดค้าง",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="SO Cycle Time",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
