from app.con_sqlalchemy import Employee
from app.ma_sqlalchemy import EmployeeSchema
from app.repositories import employee_repository
from app.app import db

def get_all_employees(data):
    try:
        search = data.get("search", "")
        items = employee_repository.get_all_employees(search)
        return {"items": EmployeeSchema(many=True).dump(items)}
    except Exception:
        raise


def create_employee(data):
    try:
        employee = Employee(
            employee_first_name=data.get("employee_first_name"),
            employee_last_name=data.get("employee_last_name"),
            citizen_id=data.get("citizen_id"),
            phone_number=data.get("phone_number"),
            email=data.get("email"),
            address=data.get("address"),
            status=data.get("status", "ว่างงาน"),
            user_id=data.get("user_id"),
            is_active=data.get("is_active", True)
        )
        employee = employee_repository.create_employee(employee)
        return EmployeeSchema().dump(employee)
    except Exception:
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
        employee.status = data.get("status", employee.status)
        employee.user_id = data.get("user_id", employee.user_id)

        db.session.flush()
        db.session.refresh(employee)
        return EmployeeSchema().dump(employee)
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