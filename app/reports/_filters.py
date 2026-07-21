"""Shared param parsers for report filters.

Keeps compose() filter handling consistent: enum multi-select (comma-separated),
booleans, and ints. Enum lookups are by member NAME, case-insensitive — every
filter enum used here has upper-case member names.
"""

from app.exception import ValidationError


def parse_enum_list(raw, enum_cls, field="value"):
    """Comma-separated string (or list) → list of enum members, or None.

    Raises ValidationError listing allowed `.value`s on an unknown token."""
    if raw is None or raw == "" or raw == []:
        return None
    if isinstance(raw, (list, tuple)):
        values = [str(v).strip() for v in raw if str(v).strip()]
    else:
        values = [v.strip() for v in str(raw).split(",") if v.strip()]
    result = []
    for v in values:
        try:
            result.append(enum_cls[v.upper()])
        except KeyError:
            allowed = [e.value for e in enum_cls]
            raise ValidationError(f"{field} ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")
    return result or None


def parse_bool(raw):
    """Truthy string/bool → bool, or None when unset."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def parse_int(raw):
    """Int-ish → int, or None when unset/invalid."""
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
