from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "item_code",      "label": "รหัสสินค้า", "width": 16},
    {"field": "item_name",      "label": "ชื่อสินค้า", "width": 32},
    {"field": "unit",           "label": "หน่วย", "width": 10, "align": "center"},
    {"field": "qty_workrun",    "label": "ใช้ใน WorkRun", "fmt": "int", "width": 14},
    {"field": "qty_testresult", "label": "ใช้ใน Test", "fmt": "int", "width": 14},
    {"field": "total_qty",      "label": "รวม", "fmt": "int", "width": 12},
]

SUMMARY_LABELS = {
    "period_from":          "ตั้งแต่",
    "period_to":            "ถึง",
    "unique_items":         "จำนวนรายการสินค้า",
    "total_qty_workrun":    "รวมที่ใช้ในการผลิต",
    "total_qty_testresult": "รวมที่ใช้ในการทดสอบ",
    "total_qty":            "รวมทั้งหมด",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Material Consumption",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
