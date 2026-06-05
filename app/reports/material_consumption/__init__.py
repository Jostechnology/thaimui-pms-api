from .compose import compose
from .render import render

NAME = "การใช้วัตถุดิบ"
DESCRIPTION = "รวมจำนวนวัตถุดิบที่ถูกใช้ใน WorkRun และ TestResult แยกตามรหัสสินค้า"
CATEGORY = "WAREHOUSE"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
    }
}
