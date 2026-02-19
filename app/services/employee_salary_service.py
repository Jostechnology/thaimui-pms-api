from app.con_sqlalchemy import Employee, User, EmployeeSalaryHistory
from app.ma_sqlalchemy import EmployeeSalaryHistorySchema, EmployeeSchema
from app.repositories import employee_salary_repository, employee_repository
from app.app import db
from flask import g
from datetime import datetime


def get_employee_salary_list(data):
	try:
		search = data.get("search", "")
		
		items = employee_salary_repository.get_employee_salary_list(search)
		return {"items": EmployeeSchema(many=True).dump(items)}
	except Exception:
		raise


def get_employee_salary_history(data):
	try:
		# ensure employee exists
		employee_id = data.get("employee_id")
		month = data.get("month", "")
		
		employee = Employee.query.get(employee_id)
		if not employee:
			raise Exception(f"Employee id {employee_id} not found")
		items = employee_salary_repository.get_salary_history(employee_id, month)
		return {"items": EmployeeSalaryHistorySchema(many=True).dump(items)}
	except Exception:
		raise


def update_employee_salary(employee_id, data):
	try:
		employee = Employee.query.get(employee_id)
		if not employee:
			raise Exception(f"Employee id {employee_id} not found")

		new_salary = data.get("new_salary")
		if new_salary is None:
			raise Exception("new_salary is required")

		# parse effective_date if provided
		effective_date = data.get("effective_date")
		if effective_date:
			try:
				# accept ISO-like strings
				effective_date = datetime.fromisoformat(effective_date)
			except Exception:
				effective_date = datetime.utcnow()
		else:
			effective_date = datetime.utcnow()

		old_salary = float(employee.salary_base or 0.0)
		new_salary = float(new_salary)

		history = EmployeeSalaryHistory(
			employee_id=employee.employee_id,
			old_salary=old_salary,
			new_salary=new_salary,
			effective_date=effective_date,
			remark=data.get("remark")
		)

		# persist history and update employee salary
		employee_salary_repository.create_salary_history(history)
		employee.salary_base = new_salary

		# Try to map created_by from auth if available
		username = getattr(g, "username", None)
		if username:
			history.created_by = username
			history.updated_by = username

		db.session.commit()
		return EmployeeSalaryHistorySchema().dump(history)
	except Exception:
		db.session.rollback()
		raise
