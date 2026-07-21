"""Picking Requests report — list of PRs with grouped status counts."""

from .compose import compose
from .render import render


NAME = "รายงาน Picking Requests"
DESCRIPTION = "สรุปคำขอเบิก: สถานะ, จำนวนรายการ"
CATEGORY = "WAREHOUSE"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": False},
        "to":   {"type": "string", "required": False},
        "status": {"type": "string", "required": False},  # PENDING|SENT|SUCCESS|FAILED (comma-list)
        "urgency_level": {"type": "string", "required": False},  # LOW|NORMAL|HIGH|URGENT (comma-list)
    }
}

__all__ = ["compose", "render", "NAME", "DESCRIPTION", "CATEGORY", "PARAMS_SCHEMA"]
