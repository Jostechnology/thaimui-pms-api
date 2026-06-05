from app.reports._helpers import render_json_default, render_xlsx_report


COLUMNS = [
    {"field": "machine_code",         "label": "รหัส", "width": 14},
    {"field": "machine_name",         "label": "ชื่อเครื่องจักร", "width": 26},
    {"field": "machine_type",         "label": "ประเภท", "width": 18},
    {"field": "working_hours_per_day","label": "ชม/วัน", "fmt": "int", "width": 10},
    {"field": "available_hours",      "label": "ชม.พร้อมใช้", "fmt": "money1", "width": 14},
    {"field": "workrun_hours",        "label": "ชม.ผลิต", "fmt": "money1", "width": 12},
    {"field": "test_hours",           "label": "ชม.ทดสอบ", "fmt": "money1", "width": 12},
    {"field": "used_hours",           "label": "ชม.ใช้งาน", "fmt": "money1", "width": 12},
    {"field": "utilization_pct",      "label": "Utilization (%)", "fmt": "money1", "width": 14},
]

SUMMARY_LABELS = {
    "period_from":            "ตั้งแต่",
    "period_to":              "ถึง",
    "machine_count":          "จำนวนเครื่องจักร",
    "total_used_hours":       "รวมชั่วโมงใช้งาน",
    "total_available_hours":  "รวมชั่วโมงพร้อมใช้",
    "fleet_utilization_pct":  "Utilization รวม (%)",
}


def render(data, fmt):
    if fmt == "xlsx":
        return render_xlsx_report(
            sheet_title="Machine Utilization",
            columns=COLUMNS, rows=data.get("rows") or [],
            summary=data.get("summary") or {}, summary_labels=SUMMARY_LABELS,
        )
    return render_json_default(data)
