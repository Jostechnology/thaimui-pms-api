from app.con_sqlalchemy import MachineType
from app.app import db
from sqlalchemy import or_


def get_machine_type_list(page, per_page, search, is_active=True):
    try:
        query = db.session.query(MachineType)
        if is_active is not None:
            query = query.filter(MachineType.is_active == is_active)
        if search:
            query = query.filter(
                or_(
                    MachineType.type_name.ilike(f"%{search}%"),
                    MachineType.type_description.ilike(f"%{search}%"),
                )
            )
        query = query.order_by(MachineType.machine_type_id.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
    except Exception:
        raise


def get_all_machine_types_active():
    """Return all active machine types (no pagination, for dropdowns)."""
    try:
        return db.session.query(MachineType).filter(MachineType.is_active == True).order_by(MachineType.type_name).all()
    except Exception:
        raise


def get_machine_type_by_id(machine_type_id):
    try:
        return db.session.query(MachineType).filter(MachineType.machine_type_id == machine_type_id).first()
    except Exception:
        raise


def create_machine_type(machine_type):
    try:
        db.session.add(machine_type)
        db.session.flush()
        return machine_type
    except Exception:
        raise


def update_machine_type(machine_type):
    try:
        db.session.flush()
        return machine_type
    except Exception:
        raise


def soft_delete_machine_type(machine_type):
    try:
        machine_type.is_active = False
        db.session.flush()
        return machine_type
    except Exception:
        raise
