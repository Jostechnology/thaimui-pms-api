"""
Default inspection checklists for test sessions (v1 — code constant, not DB-backed).

A checklist is the set of visual/functional checks an operator records per unit at
finalize. The FE fetches the relevant list (by item_group + test_type) to render blank
check rows; the operator marks PASS/FAIL/NA per unit; rows persist on the TestResultItem.

When QA needs to edit these without a deploy, promote to DB-backed InspectionTemplate
tables — see [[project_test_result_enrichment]]. Until then, edit the dicts below.

`item_group` is the product category (SalesItem.item_group). Add product-specific
overrides in PRODUCT_OVERRIDES; otherwise the generic per-test_type list is used.
"""
from app.con_sqlalchemy import TestType

# Generic checks per test type — applied when no product override matches.
DEFAULT_CHECKLISTS = {
    TestType.PROOF_LOAD: [
        "Visual condition before test",
        "No broken wires / strands",
        "No deformation or kinks",
        "No corrosion",
        "Termination / fitting condition",
        "No permanent set after test",
    ],
    TestType.BREAKING: [
        "Visual condition before test",
        "No pre-existing damage",
        "Termination / fitting condition",
    ],
    TestType.VISUAL: [
        "Surface condition",
        "Deformation",
        "Corrosion",
        "Markings legible",
        "Mechanism function",
    ],
    TestType.DIMENSIONAL: [
        "Diameter within tolerance",
        "Length within tolerance",
        "Markings legible",
    ],
}

# Product-category-specific overrides keyed by (item_group, test_type).
# Populate as QA defines per-category checklists. Example shape:
#   ("CHAIN_BLOCK", TestType.PROOF_LOAD): ["Mechanism function", "Chain integrity", ...]
PRODUCT_OVERRIDES: dict = {}


def get_checklist(item_group, test_type):
    """
    Return the ordered list of check names for an (item_group, test_type).
    Falls back to the generic per-test_type list; returns [] for unknown test_type.
    """
    if test_type is None:
        return []
    if not isinstance(test_type, TestType):
        try:
            test_type = TestType[str(test_type).strip().upper()]
        except KeyError:
            return []

    if item_group and (item_group, test_type) in PRODUCT_OVERRIDES:
        return list(PRODUCT_OVERRIDES[(item_group, test_type)])
    return list(DEFAULT_CHECKLISTS.get(test_type, []))
