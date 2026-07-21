"""Render the picking-requests report."""

from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "picking_request_code", "label": "เลขที่ใบขอเบิก", "width": 18},
    {"field": "doc_num",              "label": "เลขที่ SO", "width": 14},
    {"field": "status",               "label": "สถานะ", "width": 12, "align": "center"},
    {"field": "wms_reference",        "label": "WMS Ref", "width": 18},
    {"field": "items_count",          "label": "จำนวนรายการ", "fmt": "int", "width": 12},
    {"field": "qty_requested",        "label": "ยอดขอเบิก", "fmt": "int", "width": 12},
    {"field": "created_by",           "label": "ผู้สร้าง", "width": 16},
    {"field": "created_date",         "label": "วันที่สร้าง", "fmt": "datetime", "width": 18},
    {"field": "remark",               "label": "หมายเหตุ", "width": 30},
]


SUMMARY_LABELS = {
    "period_from":          "ตั้งแต่วันที่",
    "period_to":            "ถึงวันที่",
    "total_requests":       "จำนวนใบขอเบิก",
    "pending":              "สถานะ: รอดำเนินการ",
    "sent":                 "สถานะ: ส่งแล้ว",
    "success":              "สถานะ: สำเร็จ",
    "failed":               "สถานะ: ล้มเหลว",
    "total_items":          "รวมจำนวนรายการ",
    "total_qty_requested":  "รวมยอดขอเบิก",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Picking Requests",
            columns=COLUMNS,
            rows=data.get("rows") or [],
            summary=data.get("summary") or {},
            summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
