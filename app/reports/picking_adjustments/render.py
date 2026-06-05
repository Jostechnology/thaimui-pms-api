from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "picking_request_code",    "label": "เลขที่ใบขอเบิก", "width": 18},
    {"field": "picking_request_item_id", "label": "PRI ID", "fmt": "int", "width": 10},
    {"field": "item_code",               "label": "รหัสสินค้า", "width": 14},
    {"field": "item_name",               "label": "ชื่อสินค้า", "width": 28},
    {"field": "delta_qty",               "label": "ส่วนต่าง", "fmt": "int", "width": 10},
    {"field": "reason",                  "label": "เหตุผล", "width": 14, "align": "center"},
    {"field": "remark",                  "label": "หมายเหตุ", "width": 30},
    {"field": "created_by",              "label": "ผู้บันทึก", "width": 14},
    {"field": "created_date",            "label": "วันที่", "fmt": "datetime", "width": 18},
]

REASON_COLUMNS = [
    {"field": "reason",    "label": "เหตุผล", "width": 16, "align": "center"},
    {"field": "count",     "label": "จำนวนรายการ", "fmt": "int", "width": 14},
    {"field": "delta_sum", "label": "รวมส่วนต่าง", "fmt": "int", "width": 14},
]

SUMMARY_LABELS = {
    "period_from":       "ตั้งแต่",
    "period_to":         "ถึง",
    "adjustments_count": "จำนวนรายการ",
    "total_delta_qty":   "รวมส่วนต่าง",
    "miscount":          "MISCOUNT",
    "spillage":          "SPILLAGE",
    "correction":        "CORRECTION",
    "reallocate":        "REALLOCATE",
    "other":             "OTHER",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Adjustments",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
            extra_sheets=[{
                "title": "By Reason",
                "columns": REASON_COLUMNS,
                "rows": data.get("reason_breakdown") or [],
            }],
        )
    base = render_json_default(data)
    base["reason_breakdown"] = data.get("reason_breakdown") or []
    return base
