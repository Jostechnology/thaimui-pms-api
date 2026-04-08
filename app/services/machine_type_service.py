from app.app import db
from app.con_sqlalchemy import MachineType
from app.ma_sqlalchemy import MachineTypeSchema
from app.repositories import machine_type_repository


def get_machine_type_list(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = (data.get("search") or "").strip()
        is_active = data.get("is_active", True)
        result = machine_type_repository.get_machine_type_list(page, per_page, search, is_active)
        return {
            "items": MachineTypeSchema(many=True).dump(result.items),
            "page": page,
            "per_page": per_page,
            "total": result.total,
            "total_pages": result.pages,
        }
    except Exception:
        raise


def get_all_machine_types():
    """Return all active machine types for dropdowns."""
    try:
        types = machine_type_repository.get_all_machine_types_active()
        return MachineTypeSchema(many=True).dump(types)
    except Exception:
        raise


def get_machine_type_by_id(machine_type_id):
    try:
        mt = machine_type_repository.get_machine_type_by_id(machine_type_id)
        if not mt:
            raise Exception(f"Machine type id {machine_type_id} not found")
        return MachineTypeSchema().dump(mt)
    except Exception:
        raise


def create_machine_type(data):
    try:
        if not data.get("type_name", "").strip():
            raise Exception("type_name is required")

        mt = MachineType(
            type_name=data.get("type_name").strip(),
            type_description=data.get("type_description", "").strip() or None,
            is_active=data.get("is_active", True),
        )
        machine_type_repository.create_machine_type(mt)
        db.session.commit()
        return MachineTypeSchema().dump(mt)
    except Exception:
        db.session.rollback()
        raise


def update_machine_type(machine_type_id, data):
    try:
        mt = machine_type_repository.get_machine_type_by_id(machine_type_id)
        if not mt:
            raise Exception(f"Machine type id {machine_type_id} not found")

        if "type_name" in data:
            mt.type_name = data["type_name"].strip()
        if "type_description" in data:
            mt.type_description = data["type_description"].strip() or None
        if "is_active" in data:
            mt.is_active = data["is_active"]

        machine_type_repository.update_machine_type(mt)
        db.session.commit()
        return MachineTypeSchema().dump(mt)
    except Exception:
        db.session.rollback()
        raise