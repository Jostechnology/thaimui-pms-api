from .compose import compose
from .render import render

NAME = "การปรับยอดของเบิก"
DESCRIPTION = "บันทึก PickingItemAdjustment แยกตามเหตุผล รวมส่วนต่าง"
CATEGORY = "WAREHOUSE"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "reason": {"type": "string", "required": False},
    }
}
