"""Reports orchestration: definitions, preview (paginated JSON), export (bytes).

Each report module under app/reports/<code>/ provides compose() + render(). This
service is the only place that knows about the registry.
"""

from app.exception import NotFoundError, ValidationError
from app.reports import REPORT_REGISTRY


def list_definitions():
    """Return all report metadata for the FE gallery."""
    out = []
    for code, mod in REPORT_REGISTRY.items():
        out.append({
            "code": code,
            "name": getattr(mod, "NAME", code),
            "description": getattr(mod, "DESCRIPTION", ""),
            "category": getattr(mod, "CATEGORY", "OTHER"),
            "params_schema": getattr(mod, "PARAMS_SCHEMA", {}),
        })
    out.sort(key=lambda d: (d["category"], d["name"]))
    return out


def _get_module(code):
    if not code:
        raise ValidationError("ต้องระบุ report code")
    mod = REPORT_REGISTRY.get(code)
    if mod is None:
        raise NotFoundError(f"ไม่พบรายงาน '{code}'")
    return mod


def _validate_params(schema, params):
    """Light validation: enforce required, drop unknown keys, fill defaults."""
    if not isinstance(params, dict):
        raise ValidationError("params ต้องเป็น object")
    fields = (schema or {}).get("params", {})
    cleaned = {}
    for name, spec in fields.items():
        if name in params and params[name] not in (None, ""):
            cleaned[name] = params[name]
        elif spec.get("required"):
            raise ValidationError(f"ต้องระบุพารามิเตอร์ '{name}'")
        elif "default" in spec:
            cleaned[name] = spec["default"]
    return cleaned


def preview(code, params, page=1, per_page=25):
    """Run compose, return paginated JSON. No file generation."""
    mod = _get_module(code)
    cleaned = _validate_params(getattr(mod, "PARAMS_SCHEMA", {}), params or {})
    data = mod.compose(cleaned)
    rows = data.get("rows") or []
    total = len(rows)
    page = max(1, int(page or 1))
    per_page = max(1, int(per_page or 25))
    start = (page - 1) * per_page
    end = start + per_page
    pages = (total + per_page - 1) // per_page if per_page else 1
    # Pass through any extra top-level keys (breakdown, gantt, employee_totals,
    # ...) computed over the FULL result set so charts see all data, not just
    # the current page. Only "rows" is paginated.
    extra = {k: v for k, v in data.items() if k not in ("rows", "summary")}
    return {
        "summary": data.get("summary") or {},
        "rows": rows[start:end],
        **extra,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
    }


def export(code, params, fmt="xlsx"):
    """Run compose + render. Returns (bytes_or_dict, mime_type, filename)."""
    mod = _get_module(code)
    cleaned = _validate_params(getattr(mod, "PARAMS_SCHEMA", {}), params or {})
    data = mod.compose(cleaned)

    fmt = (fmt or "xlsx").lower()
    if fmt == "xlsx":
        payload = mod.render(data, "xlsx")
        filename = f"{code}.xlsx"
        return payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename
    if fmt == "json":
        payload = mod.render(data, "json")
        return payload, "application/json", f"{code}.json"
    raise ValidationError(f"format ไม่รองรับ: {fmt}")
