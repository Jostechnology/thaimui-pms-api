from app.con_sqlalchemy import Employee
from app.ma_sqlalchemy import EmployeeSchema
from app.repositories import employee_repository


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
            status=data.get("status", "ว่างงาน"),
            user_id=data.get("user_id"),
        )
        employee = employee_repository.create_employee(employee)
        return EmployeeSchema().dump(employee)
    except Exception:
        raise
