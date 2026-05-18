from app.con_sqlalchemy import Employee, EmployeeSalaryHistory
from sqlalchemy import extract

def get_employee_salary_list(search, page=1, per_page=10):
    try:
        query = Employee.query
        if search:
            query = query.filter(
                (Employee.employee_first_name.ilike(f"%{search}%")) |
                (Employee.employee_last_name.ilike(f"%{search}%")) |
                (Employee.citizen_id.ilike(f"%{search}%"))
            )
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
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


def get_salary_at_date(employee_id, target_date):
    """Get the employee's effective pay rates at a specific date.
    Returns tuple (new_base_salary, new_day_rate, new_ot_hourly_rate) from the most recent
    salary history record where effective_date <= target_date. Returns None if no history found.
    """
    try:
        record = (
            EmployeeSalaryHistory.query
            .filter(
                EmployeeSalaryHistory.employee_id == employee_id,
                EmployeeSalaryHistory.effective_date <= target_date
            )
            .order_by(EmployeeSalaryHistory.effective_date.desc())
            .first()
        )
        if not record:
            return None
        return (
            record.new_base_salary or 0.0,
            record.new_day_rate or 0.0,
            record.new_ot_hourly_rate or 0.0,
        )
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
