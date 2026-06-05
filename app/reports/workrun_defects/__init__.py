from .compose import compose
from .render import render

NAME = "ของเสียจากการผลิต (WorkRun)"
DESCRIPTION = "WorkRun ที่มีของเสีย (defect) พร้อมสถานะการ rework"
CATEGORY = "QUALITY"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
    }
}
