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
