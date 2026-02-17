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