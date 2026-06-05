from .compose import compose
from .render import render

NAME = "การทดสอบที่ไม่ผ่าน"
DESCRIPTION = "รายการ TestResult ที่ overall_status = FAILED รวมจำนวนชิ้นที่ตก"
CATEGORY = "QUALITY"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
    }
}
