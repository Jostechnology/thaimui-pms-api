from app.con_sqlalchemy import Employee, EmployeeSalaryHistory
from app.ma_sqlalchemy import EmployeeSalaryHistorySchema, EmployeeSchema
from app.repositories import employee_salary_repository
from app.app import db
from app.exception import NotFoundError, ValidationError
from flask import g
from datetime import datetime


def get_employee_salary_list(data):
	search = data.get("search", "")
	page = data.get("page", 1)
	per_page = data.get("per_page", 10)
	result = employee_salary_repository.get_employee_salary_list(search, page, per_page)
	return {
		"items": EmployeeSchema(many=True).dump(result["items"]),
		"total": result["total"],
		"page": result["page"],
		"pages": result["pages"],
	}


def get_employee_salary_history(data):
	employee_id = data.get("employee_id")
	month = data.get("month", "")

	employee = db.session.query(Employee).filter(Employee.employee_id == employee_id).first()
	if not employee:
		raise NotFoundError(f"Employee id {employee_id} not found")
	items = employee_salary_repository.get_salary_history(employee_id, month)
	return {"items": EmployeeSalaryHistorySchema(many=True).dump(items)}


def update_employee_salary(employee_id, data):
	"""Update one or more of base_salary / day_rate / ot_hourly_rate. Records a history row."""
	try:
		employee = db.session.query(Employee).filter(Employee.employee_id == employee_id).first()
		if not employee:
			raise NotFoundError(f"Employee id {employee_id} not found")

		new_base = data.get("new_base_salary")
		new_day = data.get("new_day_rate")
		new_ot = data.get("new_ot_hourly_rate")
		if new_base is None and new_day is None and new_ot is None:
			raise ValidationError("At least one of new_base_salary, new_day_rate, new_ot_hourly_rate is required")

		effective_date = data.get("effective_date")
		if effective_date:
			try:
				effective_date = datetime.fromisoformat(effective_date)
			except Exception:
				effective_date = datetime.utcnow()
		else:
			effective_date = datetime.utcnow()

		old_base = float(employee.base_salary or 0.0)
		old_day = float(employee.day_rate or 0.0)
		old_ot = float(employee.ot_hourly_rate or 0.0)

		new_base_v = float(new_base) if new_base is not None else old_base
		new_day_v = float(new_day) if new_day is not None else old_day
		new_ot_v = float(new_ot) if new_ot is not None else old_ot

		history = EmployeeSalaryHistory(
			employee_id=employee.employee_id,
			old_base_salary=old_base,
			new_base_salary=new_base_v,
			old_day_rate=old_day,
			new_day_rate=new_day_v,
			old_ot_hourly_rate=old_ot,
			new_ot_hourly_rate=new_ot_v,
			effective_date=effective_date,
			remark=data.get("remark"),
		)
		employee_salary_repository.create_salary_history(history)

		employee.base_salary = new_base_v
		employee.day_rate = new_day_v
		employee.ot_hourly_rate = new_ot_v

		username = getattr(g, "username", None)
		if username:
			history.created_by = username
			history.updated_by = username

		db.session.commit()
		return EmployeeSalaryHistorySchema().dump(history)
	except Exception:
		db.session.rollback()
		raise
