from app.con_sqlalchemy import EmployeeShift
from app.app import db


def get_by_employee(employee_id):
    query = db.session.query(EmployeeShift).filter(EmployeeShift.employee_id == employee_id)
    return query.first()


def create_employee_shift(employee_shift):
    db.session.add(employee_shift)
    return employee_shift


def delete_employee_shift(employee_shift):
    db.session.delete(employee_shift)
