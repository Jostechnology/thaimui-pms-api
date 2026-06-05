from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "test_result_code",   "label": "Test Result", "width": 16},
    {"field": "qc_work_order_code", "label": "QC Order", "width": 16},
    {"field": "item_code",          "label": "รหัสสินค้า", "width": 16},
    {"field": "item_name",          "label": "ชื่อสินค้า", "width": 30},
    {"field": "session_status",     "label": "Session", "width": 12, "align": "center"},
    {"field": "overall_status",     "label": "ผลรวม", "width": 12, "align": "center"},
    {"field": "claimed_qty",        "label": "จำนวนทดสอบ", "fmt": "int", "width": 12},
    {"field": "material_cost",      "label": "ต้นทุนวัตถุดิบ", "fmt": "money", "width": 14},
    {"field": "machine_cost",       "label": "ต้นทุนเครื่อง", "fmt": "money", "width": 14},
    {"field": "labor_cost",         "label": "ต้นทุนแรง", "fmt": "money", "width": 14},
    {"field": "total_cost",         "label": "รวม", "fmt": "money", "width": 14},
    {"field": "unit_cost",          "label": "ต่อหน่วย", "fmt": "money", "width": 12},
    {"field": "started_at",         "label": "เริ่มทดสอบ", "fmt": "datetime", "width": 18},
]

SUMMARY_LABELS = {
    "period_from":         "ตั้งแต่",
    "period_to":           "ถึง",
    "test_result_count":   "จำนวนการทดสอบ",
    "total_claimed_qty":   "รวมจำนวนทดสอบ",
    "total_material_cost": "รวมต้นทุนวัตถุดิบ",
    "total_machine_cost":  "รวมต้นทุนเครื่อง",
    "total_labor_cost":    "รวมต้นทุนแรง",
    "total_cost":          "รวมต้นทุนทั้งหมด",
    "avg_unit_cost":       "ต้นทุนเฉลี่ยต่อหน่วย",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Testing Cost",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
