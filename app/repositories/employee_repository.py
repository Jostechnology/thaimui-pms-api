from app.con_sqlalchemy import Employee
from app.app import db

def get_all_employees(search, status="", page=1, per_page=10):
    try:
        query = Employee.query
        if search:
            query = query.filter(
                (Employee.employee_first_name.ilike(f"%{search}%")) |
                (Employee.employee_last_name.ilike(f"%{search}%")) |
                (Employee.citizen_id.ilike(f"%{search}%"))
            )
        if status and status != "all":
             # If status is passed as a string but stored as Enum in DB
            from app.services.employee_service import _to_employee_status
            try:
                enum_status = _to_employee_status(status)
                query = query.filter(Employee.status == enum_status)
            except Exception:
                pass
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise

def get_employee_by_id(employee_id):
    try:
        employee = Employee.query.get(employee_id)
        return employee
    except Exception:
        raise

def create_employee(employee):
    try:
        db.session.add(employee)
        return employee
    except Exception:
        db.session.rollback()
        raise

def update_employee(employee):
    try:
        db.session.flush()
        db.session.refresh(employee)
        return employee
    except Exception:
        db.session.rollback()
        raise


def delete_employee(employee_id):
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise Exception(f"Employee id {employee_id} not found")

        db.session.delete(employee)
        db.session.commit()
        return {"message": f"Deleted employee id {employee_id} successfully"}
    except Exception:
        db.session.rollback()
        raise