from .compose import compose
from .render import render

NAME = "การใช้งานเครื่องจักร"
DESCRIPTION = "ชั่วโมงใช้งานเครื่องจักรเทียบกับชั่วโมงพร้อมใช้ในช่วงเวลา"
CATEGORY = "PRODUCTION"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "machine_id": {"type": "number", "required": False},
    }
}
