from app.ma_sqlalchemy import EmployeeSchema
from app.repositories import employee_repository


def get_all_employees(data):
    try:
        search = data.get("search", "")
        items =  employee_repository.get_all_employees(search)
        return {"items": EmployeeSchema(many=True).dump(items)}
    except Exception:
        raise


def create_employee(data):
    try:
        employee = employee_repository.create_employee(data)
        return EmployeeSchema().dump(employee)
    except Exception:
        raise
