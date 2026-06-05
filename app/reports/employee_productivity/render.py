from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "employee_name",         "label": "พนักงาน", "width": 24},
    {"field": "assignments",           "label": "งาน", "fmt": "int", "width": 10},
    {"field": "work_runs",             "label": "WorkRun", "fmt": "int", "width": 10},
    {"field": "hours_worked",          "label": "ชั่วโมงทำงาน", "fmt": "money1", "width": 14},
    {"field": "attributed_usable_qty", "label": "ผลิตได้ (เฉลี่ย)", "fmt": "money1", "width": 16},
    {"field": "attributed_defect_qty", "label": "ของเสีย (เฉลี่ย)", "fmt": "money1", "width": 16},
    {"field": "output_per_hour",       "label": "ชิ้น/ชั่วโมง", "fmt": "money1", "width": 12},
]

SUMMARY_LABELS = {
    "period_from":      "ตั้งแต่",
    "period_to":        "ถึง",
    "employees":        "จำนวนพนักงาน",
    "total_hours":      "รวมชั่วโมงทำงาน",
    "total_usable_qty": "รวมผลิตได้ (เฉลี่ย)",
    "total_defect_qty": "รวมของเสีย (เฉลี่ย)",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Employee Productivity",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
