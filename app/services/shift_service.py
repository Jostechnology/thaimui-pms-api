from datetime import time
from app.app import db
from app.con_sqlalchemy import Shift
from app.exception import NotFoundError, ValidationError
from app.repositories import shift_repository


_VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}


def _parse_time(value):
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        parts = value.split(":")
        if len(parts) < 2:
            raise ValidationError(f"Invalid time: {value}")
        h, m = int(parts[0]), int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        return time(h, m, s)
    raise ValidationError(f"Invalid time: {value}")


def _normalize_work_days(value):
    if value is None:
        return None
    if isinstance(value, list):
        tokens = [str(t).strip().upper() for t in value if str(t).strip()]
    else:
        tokens = [t.strip().upper() for t in str(value).split(",") if t.strip()]
    for t in tokens:
        if t not in _VALID_DAYS:
            raise ValidationError(f"Invalid work day token: {t}")
    return ",".join(tokens)


def get_all_shifts(data):
    search = data.get("search", "")
    page = data.get("page", 1)
    per_page = data.get("per_page", 10)
    result = shift_repository.get_all_shifts(search, page, per_page)
    return result


def get_shift_by_id(shift_id):
    shift = shift_repository.get_shift_by_id(shift_id)
    if not shift:
        raise NotFoundError(f"Shift id {shift_id} not found")
    return shift


def get_default_shift():
    shift = shift_repository.get_default_shift()
    if not shift:
        raise NotFoundError("Default shift not configured")
    return shift


def create_shift(data):
    try:
        is_default = bool(data.get("is_default", False))
        if is_default:
            shift_repository.clear_default_flag()
        shift = Shift(
            name=data.get("name", "DEFAULT"),
            start_time=_parse_time(data.get("start_time", "08:00")),
            end_time=_parse_time(data.get("end_time", "17:00")),
            work_days=_normalize_work_days(data.get("work_days", "MON,TUE,WED,THU,FRI")),
            ot_multiplier=float(data.get("ot_multiplier", 1.5)),
            weekend_multiplier=float(data.get("weekend_multiplier", 2.0)),
            holiday_multiplier=float(data.get("holiday_multiplier", 3.0)),
            is_default=is_default,
        )
        shift_repository.create_shift(shift)
        db.session.commit()
        return shift
    except Exception:
        db.session.rollback()
        raise


def update_shift(shift_id, data):
    try:
        shift = get_shift_by_id(shift_id)
        if "name" in data:
            shift.name = data["name"]
        if "start_time" in data:
            shift.start_time = _parse_time(data["start_time"])
        if "end_time" in data:
            shift.end_time = _parse_time(data["end_time"])
        if "work_days" in data:
            shift.work_days = _normalize_work_days(data["work_days"])
        if "ot_multiplier" in data:
            shift.ot_multiplier = float(data["ot_multiplier"])
        if "weekend_multiplier" in data:
            shift.weekend_multiplier = float(data["weekend_multiplier"])
        if "holiday_multiplier" in data:
            shift.holiday_multiplier = float(data["holiday_multiplier"])
        if "is_default" in data:
            new_default = bool(data["is_default"])
            if new_default and not shift.is_default:
                shift_repository.clear_default_flag()
            shift.is_default = new_default
        db.session.commit()
        return shift
    except Exception:
        db.session.rollback()
        raise


def delete_shift(shift_id):
    try:
        shift = get_shift_by_id(shift_id)
        if shift.is_default:
            raise ValidationError("Cannot delete the default shift")
        db.session.delete(shift)
        db.session.commit()
        return {"message": f"Deleted shift id {shift_id}"}
    except Exception:
        db.session.rollback()
        raise
