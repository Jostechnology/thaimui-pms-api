from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "lot_number",             "label": "Lot", "width": 16},
    {"field": "work_run_id",            "label": "WorkRun", "fmt": "int", "width": 10},
    {"field": "item_code",              "label": "รหัสสินค้า", "width": 16},
    {"field": "item_name",              "label": "ชื่อสินค้า", "width": 30},
    {"field": "planned_qty",            "label": "วางแผน", "fmt": "int", "width": 10},
    {"field": "usable_qty",             "label": "ผลิตได้", "fmt": "int", "width": 10},
    {"field": "defect_qty",             "label": "ของเสีย", "fmt": "int", "width": 10},
    {"field": "consumed_defect_qty",    "label": "ใช้ rework แล้ว", "fmt": "int", "width": 14},
    {"field": "outstanding_defect_qty", "label": "ของเสียคงค้าง", "fmt": "int", "width": 14},
    {"field": "defect_rate_pct",        "label": "อัตราของเสีย (%)", "fmt": "money1", "width": 14},
    {"field": "completed_date",         "label": "วันเสร็จ", "fmt": "datetime", "width": 18},
    {"field": "remark",                 "label": "หมายเหตุ", "width": 30},
]

SUMMARY_LABELS = {
    "period_from":                   "ตั้งแต่",
    "period_to":                     "ถึง",
    "workrun_count":                 "จำนวน WorkRun ที่มีของเสีย",
    "total_planned_qty":             "รวมวางแผน",
    "total_usable_qty":              "รวมผลิตได้",
    "total_defect_qty":              "รวมของเสีย",
    "total_outstanding_defect_qty":  "รวมของเสียคงค้าง",
    "runs_with_rework":              "WorkRun ที่ rework แล้ว",
    "defect_rate_pct":               "อัตราของเสียรวม (%)",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="WorkRun Defects",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
