from .compose import compose
from .render import render

NAME = "ต้นทุนการเทส"
DESCRIPTION = "สรุปต้นทุน TestResult: วัตถุดิบ, เครื่อง, ค่าแรง, รวม"
CATEGORY = "COST"
PARAMS_SCHEMA = {
    "params": {
        "from": {"type": "string", "required": True},
        "to":   {"type": "string", "required": True},
        "overall_status": {"type": "string", "required": False},  # PASSED|FAILED (comma-list)
        "session_status": {"type": "string", "required": False},  # PENDING|INPROGRESS|PAUSED|COMPLETED (comma-list)
        "test_type": {"type": "string", "required": False},       # PROOF_LOAD|BREAKING|VISUAL|DIMENSIONAL (comma-list)
    }
}
