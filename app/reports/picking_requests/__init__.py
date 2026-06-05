"""Picking Requests report — list of PRs with verify delta, grouped status counts."""

from .compose import compose
from .render import render


NAME = "รายงาน Picking Requests"
DESCRIPTION = "สรุปคำขอเบิก: สถานะ, จำนวนรายการ, ส่วนต่างจากการตรวจรับ"
CATEGORY = "WAREHOUSE"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": False},
        "to":   {"type": "string", "required": False},
        "status": {"type": "string", "required": False},  # PENDING|SENT|SUCCESS|FAILED
    }
}

__all__ = ["compose", "render", "NAME", "DESCRIPTION", "CATEGORY", "PARAMS_SCHEMA"]
