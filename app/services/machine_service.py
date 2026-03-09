from datetime import datetime, time, date

from app.app import db
from app.con_sqlalchemy import Machine, MachineStatus
from app.ma_sqlalchemy import MachineSchema
from app.repositories import machine_repository


def _normalize_search(val):
    if val is None:
        return ""
    return str(val).strip()

def _to_machine_status(val):
    if val is None:
        return MachineStatus.IDLE

    if isinstance(val, MachineStatus):
        return val

    if isinstance(val, str):
        text = val.strip()
        try:
            return MachineStatus[text.upper()]
        except Exception:
            pass

        for item in MachineStatus:
            if item.value == text.upper():
                return item

    raise ValueError(f"Invalid machine status: {val}")

def _to_bool(val, default=True):
    if val is None:
        return default

    if isinstance(val, bool):
        return val

    if isinstance(val, str):
        lowered = val.strip().lower()
        if lowered in ("true", "1", "yes", "y"):
            return True
        if lowered in ("false", "0", "no", "n"):
            return False

    return default

def _to_purchase_date(val):
    if val in (None, ""):
        return None

    if isinstance(val, datetime):
        return val

    if isinstance(val, date):
        return datetime.combine(val, time.min)

    if isinstance(val, str):
        text = val.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return datetime.combine(datetime.strptime(text, "%Y-%m-%d").date(), time.min)

    raise ValueError("Invalid purchase_date. Expected ISO datetime or YYYY-MM-DD")

def get_machine_list(data):
    try:
        search = _normalize_search(data.get("search") or data.get("keyword") or data.get("query"))
        status = data.get("status", "")
        is_active = data.get("is_active", None)
        items = machine_repository.get_machine_list(search, status, is_active)
        return {
            "items": MachineSchema(many=True).dump(items),
            "filters": {
                "search": search,
                "status": status,
                "is_active": is_active,
            },
            "total": len(items),
        }
    except Exception:
        raise

def get_machine_by_id(machine_id):
    try:
        machine = Machine.query.get(machine_id)
        if not machine:
            raise Exception(f"Machine id {machine_id} not found")
        return MachineSchema().dump(machine)
    except Exception:
        raise

def create_machine(data):
    try:
        machine = Machine(
            machine_code=data.get("machine_code"),
            machine_name=data.get("machine_name"),
            machine_description=data.get("machine_description"),
            manufacturer=data.get("manufacturer"),
            purchase_date=_to_purchase_date(data.get("purchase_date")),
            status=_to_machine_status(data.get("status")),
            is_active=_to_bool(data.get("is_active"), True),
        )

        if not machine.machine_code:
            raise Exception("machine_code is required")

        if not machine.machine_name:
            raise Exception("machine_name is required")

        machine = machine_repository.create_machine(machine)
        db.session.commit()
        return MachineSchema().dump(machine)
    except Exception:
        db.session.rollback()
        raise

def update_machine(machine_id, data):
    try:
        machine = machine_repository.get_machine_by_id(machine_id)
        if not machine:
            raise Exception(f"Machine id {machine_id} not found")

        machine.machine_code = data.get("machine_code", machine.machine_code)
        machine.machine_name = data.get("machine_name", machine.machine_name)
        machine.machine_description = data.get("machine_description", machine.machine_description)
        machine.manufacturer = data.get("manufacturer", machine.manufacturer)

        if "purchase_date" in data:
            machine.purchase_date = _to_purchase_date(data.get("purchase_date"))

        if "status" in data:
            machine.status = _to_machine_status(data.get("status"))

        if "is_active" in data:
            machine.is_active = _to_bool(data.get("is_active"), machine.is_active)

        machine = machine_repository.update_machine(machine)
        db.session.commit()
        return MachineSchema().dump(machine)
    except Exception:
        db.session.rollback()
        raise


def delete_machine(machine_id):
    try:
        machine = machine_repository.get_machine_by_id(machine_id)
        if not machine:
            raise Exception(f"Machine id {machine_id} not found")

        machine_repository.soft_delete_machine(machine)
        db.session.commit()
        return {
            "machine_id": machine.machine_id,
            "message": f"Machine id {machine_id} marked inactive successfully",
            "is_active": machine.is_active,
        }
    except Exception:
        db.session.rollback()
        raise