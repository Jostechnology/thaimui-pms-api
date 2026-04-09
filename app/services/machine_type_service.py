from app.app import db
from app.con_sqlalchemy import MachineType
from app.exception import NotFoundError, MissingFieldsError
from app.repositories import machine_type_repository


def get_machine_type_list(data):
    page = data.get("page", 1)
    per_page = data.get("per_page", 10)
    search = (data.get("search") or "").strip()
    is_active = data.get("is_active", True)
    return machine_type_repository.get_machine_type_list(page, per_page, search, is_active)


def get_all_machine_types():
    return machine_type_repository.get_all_machine_types_active()


def get_machine_type_by_id(machine_type_id):
    mt = machine_type_repository.get_machine_type_by_id(machine_type_id)
    if not mt:
        raise NotFoundError(f"Machine type id {machine_type_id} not found")
    return mt


def create_machine_type(data):
    if not data.get("type_name", "").strip():
        raise MissingFieldsError("type_name is required")
    mt = MachineType(
        type_name=data["type_name"].strip(),
        type_description=data.get("type_description", "").strip() or None,
        is_active=data.get("is_active", True),
    )
    machine_type_repository.create_machine_type(mt)
    db.session.commit()
    return mt


def update_machine_type(machine_type_id, data):
    mt = machine_type_repository.get_machine_type_by_id(machine_type_id)
    if not mt:
        raise NotFoundError(f"Machine type id {machine_type_id} not found")
    if "type_name" in data:
        mt.type_name = data["type_name"].strip()
    if "type_description" in data:
        mt.type_description = data["type_description"].strip() or None
    if "is_active" in data:
        mt.is_active = data["is_active"]
    machine_type_repository.update_machine_type(mt)
    db.session.commit()
    return mt


def delete_machine_type(machine_type_id):
    mt = machine_type_repository.get_machine_type_by_id(machine_type_id)
    if not mt:
        raise NotFoundError(f"Machine type id {machine_type_id} not found")
    machine_type_repository.soft_delete_machine_type(mt)
    db.session.commit()
    return mt
