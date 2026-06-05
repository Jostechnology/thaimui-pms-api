from .compose import compose
from .render import render

NAME = "ระยะเวลาทำใบสั่งขาย"
DESCRIPTION = "เวลาตั้งแต่สร้าง SO จนถึงเสร็จสิ้น เพื่อระบุคอขวด"
CATEGORY = "SALES"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "status": {"type": "string", "required": False},  # INPROGRESS|COMPLETED
    }
}
