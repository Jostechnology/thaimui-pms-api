from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "lot_number",     "label": "Lot", "width": 16},
    {"field": "work_run_id",    "label": "WorkRun", "fmt": "int", "width": 10},
    {"field": "work_order_id",  "label": "WorkOrder", "fmt": "int", "width": 12},
    {"field": "item_code",      "label": "รหัสสินค้า", "width": 16},
    {"field": "item_name",      "label": "ชื่อสินค้า", "width": 30},
    {"field": "status",         "label": "สถานะ", "width": 12, "align": "center"},
    {"field": "planned_qty",    "label": "วางแผน", "fmt": "int", "width": 10},
    {"field": "usable_qty",     "label": "ผลิตได้", "fmt": "int", "width": 10},
    {"field": "material_cost",  "label": "ต้นทุนวัตถุดิบ", "fmt": "money", "width": 14},
    {"field": "machine_cost",   "label": "ต้นทุนเครื่อง", "fmt": "money", "width": 14},
    {"field": "labor_cost",     "label": "ต้นทุนแรง", "fmt": "money", "width": 14},
    {"field": "total_cost",     "label": "รวม", "fmt": "money", "width": 14},
    {"field": "unit_cost",      "label": "ต่อหน่วย", "fmt": "money", "width": 12},
    {"field": "completed_date", "label": "วันเสร็จ", "fmt": "datetime", "width": 18},
]

SUMMARY_LABELS = {
    "period_from":         "ตั้งแต่",
    "period_to":           "ถึง",
    "workrun_count":       "จำนวน WorkRun",
    "total_planned_qty":   "รวมจำนวนที่วางแผน",
    "total_usable_qty":    "รวมผลิตได้",
    "total_material_cost": "รวมต้นทุนวัตถุดิบ",
    "total_machine_cost":  "รวมต้นทุนเครื่อง",
    "total_labor_cost":    "รวมต้นทุนแรง",
    "total_cost":          "รวมต้นทุนทั้งหมด",
    "avg_unit_cost":       "ต้นทุนเฉลี่ยต่อหน่วย",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Production Cost",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
