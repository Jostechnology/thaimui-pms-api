from .compose import compose
from .render import render

NAME = "ต้นทุนการผลิต"
DESCRIPTION = "สรุปต้นทุน WorkRun: วัตถุดิบ, เครื่องจักร, ค่าแรง, รวม"
CATEGORY = "COST"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "work_order_id": {"type": "number", "required": False},
        "workrun_status": {"type": "string", "required": False},  # PENDING|INPROGRESS|PAUSED|COMPLETED (comma-list)
    }
}
