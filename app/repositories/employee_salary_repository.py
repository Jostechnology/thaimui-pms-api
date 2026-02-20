from app.con_sqlalchemy import Employee, EmployeeSalaryHistory
from sqlalchemy import extract

def get_employee_salary_list(search):
    try:
        query = Employee.query
        if search:
            query = query.filter(
                (Employee.employee_first_name.ilike(f"%{search}%")) |
                (Employee.employee_last_name.ilike(f"%{search}%")) |
                (Employee.citizen_id.ilike(f"%{search}%"))
            )
        return query.all()
    except Exception:
        raise


def get_salary_history(employee_id,month):
    try:
        query = EmployeeSalaryHistory.query.filter_by(employee_id=employee_id).order_by(EmployeeSalaryHistory.effective_date.desc())

        if month:
            filter_year, filter_month = map(int, month.split('-'))
            query = query.filter(
                extract('year', EmployeeSalaryHistory.effective_date) == filter_year,
                extract('month', EmployeeSalaryHistory.effective_date) == filter_month
            )
        return query.all()
    except Exception:
        raise


def create_salary_history(history):
    try:
        # history is an instance of EmployeeSalaryHistory
        from app.app import db
        db.session.add(history)
        return history
    except Exception:
        raise
