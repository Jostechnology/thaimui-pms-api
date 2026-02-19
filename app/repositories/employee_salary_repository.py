from app.con_sqlalchemy import Employee, EmployeeSalaryHistory


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


def get_salary_history(employee_id):
    try:
        items = EmployeeSalaryHistory.query.filter_by(employee_id=employee_id).order_by(EmployeeSalaryHistory.effective_date.desc()).all()
        return items
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
