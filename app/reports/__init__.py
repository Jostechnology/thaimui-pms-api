"""Reports module — registry of report definitions.

Each report is a sub-package under app/reports/<code>/ exposing:
    NAME, DESCRIPTION, CATEGORY, PARAMS_SCHEMA (dict)
    compose(params) -> {"summary": {...}, "rows": [...]}
    render(data, fmt: "json"|"xlsx") -> dict (json) or bytes (xlsx)
"""

from importlib import import_module


# (code, module_path). Add new reports here.
_REPORT_CODES = [
    ("picking_requests",      "app.reports.picking_requests"),
    ("worker_time",           "app.reports.worker_time"),
    ("employee_productivity", "app.reports.employee_productivity"),
    ("production_cost",       "app.reports.production_cost"),
    ("testing_cost",          "app.reports.testing_cost"),
    ("failed_tests",          "app.reports.failed_tests"),
    ("workrun_defects",       "app.reports.workrun_defects"),
    ("machine_utilization",   "app.reports.machine_utilization"),
    ("so_cycle_time",         "app.reports.so_cycle_time"),
]


def _build_registry():
    registry = {}
    for code, module_path in _REPORT_CODES:
        registry[code] = import_module(module_path)
    return registry


REPORT_REGISTRY = _build_registry()
