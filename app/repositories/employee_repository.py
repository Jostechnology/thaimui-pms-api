from app.con_sqlalchemy import Employee
from app.app import db

def get_all_employees(search):
    try:
        query = Employee.query
        if search:
            query = query.filter(Employee.employee_id.ilike(f"%{search}%"))
        items = query.all()
        return items
    except Exception:
        raise


def create_employee(employee):
    try:
        db.session.add(employee)
        db.session.flush()
        return employee
    except Exception:
        db.session.rollback()
        raise
