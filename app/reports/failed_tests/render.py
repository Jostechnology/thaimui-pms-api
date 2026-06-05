from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "test_result_code",   "label": "Test Result", "width": 16},
    {"field": "qc_work_order_code", "label": "QC Order", "width": 16},
    {"field": "item_code",          "label": "รหัสสินค้า", "width": 16},
    {"field": "item_name",          "label": "ชื่อสินค้า", "width": 30},
    {"field": "claimed_qty",        "label": "จำนวนทดสอบ", "fmt": "int", "width": 12},
    {"field": "failed_qty",         "label": "ไม่ผ่าน", "fmt": "int", "width": 10},
    {"field": "passed_qty",         "label": "ผ่าน", "fmt": "int", "width": 10},
    {"field": "failed_units",       "label": "ลำดับชิ้นที่ตก", "width": 24},
    {"field": "started_at",         "label": "เริ่มทดสอบ", "fmt": "datetime", "width": 18},
    {"field": "remark",             "label": "หมายเหตุ", "width": 30},
]

SUMMARY_LABELS = {
    "period_from":        "ตั้งแต่",
    "period_to":          "ถึง",
    "failed_tests":       "จำนวนการทดสอบที่ตก",
    "total_claimed_qty":  "รวมจำนวนทดสอบ",
    "total_failed_items": "รวมจำนวนชิ้นที่ตก",
    "fail_rate_pct":      "อัตราชิ้นที่ตก (%)",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Failed Tests",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
