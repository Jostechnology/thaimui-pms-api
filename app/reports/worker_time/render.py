"""Render worker-time report."""

from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "employee_name", "label": "พนักงาน", "width": 24},
    {"field": "lot_number",    "label": "Lot", "width": 14},
    {"field": "work_run_id",   "label": "WorkRun ID", "fmt": "int", "width": 12},
    {"field": "from_time",     "label": "เริ่ม", "fmt": "datetime", "width": 18},
    {"field": "to_time",       "label": "สิ้นสุด", "fmt": "datetime", "width": 18},
    {"field": "gross_hours",   "label": "ชั่วโมงรวม", "fmt": "money1", "width": 12},
    {"field": "break_hours",   "label": "ชั่วโมงพัก", "fmt": "money1", "width": 12},
    {"field": "net_hours",     "label": "ชั่วโมงสุทธิ", "fmt": "money1", "width": 12},
]

TOTAL_COLUMNS = [
    {"field": "employee_name", "label": "พนักงาน", "width": 24},
    {"field": "assignments",   "label": "จำนวนงาน", "fmt": "int", "width": 12},
    {"field": "work_runs",     "label": "จำนวน WorkRun", "fmt": "int", "width": 14},
    {"field": "gross_hours",   "label": "ชั่วโมงรวม", "fmt": "money1", "width": 12},
    {"field": "net_hours",     "label": "ชั่วโมงสุทธิ", "fmt": "money1", "width": 12},
]

SUMMARY_LABELS = {
    "period_from":        "ตั้งแต่",
    "period_to":          "ถึง",
    "assignments_count":  "จำนวนการมอบหมายงาน",
    "unique_employees":   "จำนวนพนักงาน",
    "total_gross_hours":  "ชั่วโมงรวม",
    "total_net_hours":    "ชั่วโมงสุทธิ",
    "open_assignments":   "งานที่ยังไม่ปิด",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Worker Time",
            columns=COLUMNS,
            rows=data.get("rows") or [],
            summary=data.get("summary") or {},
            summary_labels=SUMMARY_LABELS,
            extra_sheets=[
                {"title": "Employee Totals", "columns": TOTAL_COLUMNS, "rows": data.get("employee_totals") or []},
            ],
        )
    # JSON: include gantt + totals
    base = render_json_default(data)
    base["gantt"] = data.get("gantt") or []
    base["employee_totals"] = data.get("employee_totals") or []
    return base
