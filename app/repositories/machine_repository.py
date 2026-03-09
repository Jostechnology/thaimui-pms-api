from app.con_sqlalchemy import Machine
from app.app import db


def get_machine_list(search="", status="", is_active=None):
    try:
        query = Machine.query

        if search:
            query = query.filter(
                (Machine.machine_code.ilike(f"%{search}%")) |
                (Machine.machine_name.ilike(f"%{search}%")) |
                (Machine.manufacturer.ilike(f"%{search}%")) |
                (Machine.machine_description.ilike(f"%{search}%"))
            )

        if status and status != "all":
            from app.services.machine_service import _to_machine_status
            try:
                enum_status = _to_machine_status(status)
                query = query.filter(Machine.status == enum_status)
            except Exception:
                pass

        if is_active not in (None, "", "all"):
            if isinstance(is_active, str):
                lowered = is_active.strip().lower()
                if lowered in ("true", "1", "yes", "active"):
                    is_active = True
                elif lowered in ("false", "0", "no", "inactive"):
                    is_active = False
                else:
                    is_active = None

            if isinstance(is_active, bool):
                query = query.filter(Machine.is_active == is_active)

        return query.order_by(Machine.machine_code.asc()).all()
    except Exception:
        raise

def get_machine_by_id(machine_id):
    try:
        return Machine.query.get(machine_id)
    except Exception:
        raise

def create_machine(machine):
    try:
        db.session.add(machine)
        return machine
    except Exception:
        db.session.rollback()
        raise

def update_machine(machine):
    try:
        db.session.flush()
        db.session.refresh(machine)
        return machine
    except Exception:
        db.session.rollback()
        raise


def soft_delete_machine(machine):
    try:
        machine.is_active = False
        db.session.flush()
        db.session.refresh(machine)
        return machine
    except Exception:
        db.session.rollback()
        raise