"""Worker working time — per-assignment + per-employee totals + Gantt-friendly tasks."""

from .compose import compose
from .render import render


NAME = "เวลาทำงานของพนักงาน"
DESCRIPTION = "บันทึกการทำงานของพนักงานต่อ WorkRun รวมชั่วโมงและช่วงเวลา (รองรับ Gantt)"
CATEGORY = "HR"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "employee_id": {"type": "number", "required": False},
        "work_order_id": {"type": "number", "required": False},
        "workrun_status": {"type": "string", "required": False},  # PENDING|INPROGRESS|PAUSED|COMPLETED (comma-list)
        "open_only": {"type": "boolean", "required": False},
    }
}

__all__ = ["compose", "render", "NAME", "DESCRIPTION", "CATEGORY", "PARAMS_SCHEMA"]
