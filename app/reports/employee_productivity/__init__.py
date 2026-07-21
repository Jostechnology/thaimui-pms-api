from .compose import compose
from .render import render

NAME = "ประสิทธิภาพพนักงาน"
DESCRIPTION = "จำนวนชิ้นผลิตได้ที่กระจายตามชั่วโมงทำงานของแต่ละพนักงาน"
CATEGORY = "HR"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "employee_id": {"type": "number", "required": False},
        "work_order_id": {"type": "number", "required": False},
    }
}
