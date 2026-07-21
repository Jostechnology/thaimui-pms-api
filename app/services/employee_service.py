import uuid

from app.con_sqlalchemy import Employee, User, EmployeeStatus
from app.exception import NotFoundError
from app.ma_sqlalchemy import EmployeeSchema
from app.repositories import employee_repository
from app.services import storage_service
from app.app import db
from flask import g


def _to_employee_status(val):
    if val is None:
        # default to the first enum member that represents UNEMPLOYED/idle
        for m in EmployeeStatus:
            # try to find a reasonable default by matching English-like names
            if str(m.name).upper() in ("UNEMPLOYED"):
                return m
        # fallback to first member
        return list(EmployeeStatus)[0]
    if isinstance(val, EmployeeStatus):
        return val
    if isinstance(val, str):
        s = val.strip()
        # try match by enum name
        try:
            return EmployeeStatus[s.upper()]
        except Exception:
            pass
        # try match by enum value (Thai labels)
        for m in EmployeeStatus:
            if m.value == s:
                return m
    raise ValueError(f"Invalid status: {val}")

def get_all_employees(data):
    try:
        search = data.get("search", "")
        status = data.get("status", "")
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        result = employee_repository.get_all_employees(search, status, page, per_page)
        return {
            "items": EmployeeSchema(many=True).dump(result["items"]),
            "total": result["total"],
            "page": result["page"],
            "pages": result["pages"],
        }
    except Exception:
        raise

def get_employee_by_id(employee_id):
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise Exception(f"Employee id {employee_id} not found")
        return EmployeeSchema().dump(employee)
    except Exception:
        raise
    
def get_employee_by_id(employee_id):
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise Exception(f"Employee id {employee_id} not found")
        return EmployeeSchema().dump(employee)
    except Exception:
        raise


def create_employee(data):
    try:
        # Use module-level helper `_to_employee_status`

        employee = Employee(
            employee_first_name=data.get("employee_first_name"),
            employee_last_name=data.get("employee_last_name"),
            citizen_id=data.get("citizen_id"),
            phone_number=data.get("phone_number"),
            email=data.get("email"),
            address=data.get("address"),
            status=_to_employee_status(data.get("status")),
            user_id=data.get("user_id"),
            base_salary=data.get("base_salary", 0.0),
            day_rate=data.get("day_rate", 0.0),
            ot_hourly_rate=data.get("ot_hourly_rate", 0.0),
            is_active=data.get("is_active", True)
        )
        # If user_id wasn't provided by client, try to map from authenticated username
        if not employee.user_id:
            username = getattr(g, "username", None)
            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    employee.user_id = user.user_id
        # If still no user_id, raise a clear exception so client can correct input
        if not employee.user_id:
            raise Exception("user_id is required to create an employee. Provide user_id or ensure the authenticated user maps to an existing user record.")
        employee = employee_repository.create_employee(employee)
        db.session.commit()
        return EmployeeSchema().dump(employee)
    except Exception:
        db.session.rollback()
        raise


def update_employee(employee_id, data):
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise Exception(f"Employee id {employee_id} not found")

        employee.employee_first_name = data.get("employee_first_name", employee.employee_first_name)
        employee.employee_last_name = data.get("employee_last_name", employee.employee_last_name)
        employee.citizen_id = data.get("citizen_id", employee.citizen_id)
        employee.phone_number = data.get("phone_number", employee.phone_number)
        employee.email = data.get("email", employee.email)
        employee.address = data.get("address", employee.address)
        if "status" in data:
            # convert incoming status to Enum member (keep existing if invalid)
            try:
                employee.status = _to_employee_status(data.get("status"))
            except Exception:
                pass
        employee.user_id = data.get("user_id", employee.user_id)
        if "is_active" in data:
            employee.is_active = bool(data.get("is_active"))
        db.session.flush()
        db.session.refresh(employee)
        db.session.commit()
        return EmployeeSchema().dump(employee)
    except Exception:
        db.session.rollback()
        raise


def delete_employee(employee_id):
    """Soft delete — mark inactive so assignment/salary history stays intact."""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise NotFoundError(f"Employee id {employee_id} not found")
        employee.is_active = False
        db.session.commit()
        return {
            "employee_id": employee.employee_id,
            "message": f"Employee id {employee_id} marked inactive successfully",
            "is_active": employee.is_active,
        }
    except Exception:
        db.session.rollback()
        raise


def set_employee_photo(employee_id, data):
    """Upload/replace the employee profile photo (base64 data URL → MinIO)."""
    employee = Employee.query.get(employee_id)
    if not employee:
        raise NotFoundError(f"Employee id {employee_id} not found")

    image_bytes, content_type = storage_service.decode_data_url(data.get("image_base64"))
    object_key = f"employee/{employee_id}/photo/{uuid.uuid4().hex}"
    try:
        storage_service.upload_image(image_bytes, object_key, content_type=content_type)
        old_key = employee.photo_key
        employee.photo_key = object_key
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    if old_key:
        try:
            storage_service.delete_image(old_key)
        except Exception:
            pass  # best-effort cleanup; DB already points to the new photo
    return EmployeeSchema().dump(employee)


def delete_employee_photo(employee_id):
    """Remove the employee profile photo (storage cleanup is best-effort)."""
    employee = Employee.query.get(employee_id)
    if not employee:
        raise NotFoundError(f"Employee id {employee_id} not found")
    if employee.photo_key:
        try:
            storage_service.delete_image(employee.photo_key)
        except Exception:
            pass
        employee.photo_key = None
        db.session.commit()
    return EmployeeSchema().dump(employee)