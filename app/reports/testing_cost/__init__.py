from .compose import compose
from .render import render

NAME = "ต้นทุนการเทส"
DESCRIPTION = "สรุปต้นทุน TestResult: วัตถุดิบ, เครื่อง, ค่าแรง, รวม"
CATEGORY = "COST"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
    }
}
