from app.con_sqlalchemy import Employee
from app.app import db

def get_all_employees(page, limit, search):
    try:
        query = Employee.query
        if search:
            query = query.filter(Employee.employee_id.ilike(f"%{search}%"))
        query = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": query.items, "total_pages": query.pages}
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
        db.session.add(employee)
        db.session.commit()
        return employee
    except Exception:
        db.session.rollback()
        raise
