from app.app import db
from app.con_sqlalchemy import Employee, EmployeeShift
from app.exception import NotFoundError
from app.repositories import employee_shift_repository
from app.services.shift_service import _parse_time, _normalize_work_days


def get_employee_shift(employee_id):
    return employee_shift_repository.get_by_employee(employee_id)


def upsert_employee_shift(employee_id, data):
    """Full override. Create or replace the employee's shift override."""
    try:
        employee = db.session.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise NotFoundError(f"Employee id {employee_id} not found")

        existing = employee_shift_repository.get_by_employee(employee_id)
        start_time = _parse_time(data.get("start_time"))
        end_time = _parse_time(data.get("end_time"))
        work_days = _normalize_work_days(data.get("work_days"))

        if existing:
            existing.start_time = start_time or existing.start_time
            existing.end_time = end_time or existing.end_time
            if work_days is not None:
                existing.work_days = work_days
            result = existing
        else:
            shift = EmployeeShift(
                employee_id=employee_id,
                start_time=start_time,
                end_time=end_time,
                work_days=work_days or "MON,TUE,WED,THU,FRI",
            )
            employee_shift_repository.create_employee_shift(shift)
            result = shift
        db.session.commit()
        return result
    except Exception:
        db.session.rollback()
        raise


def delete_employee_shift(employee_id):
    try:
        existing = employee_shift_repository.get_by_employee(employee_id)
        if not existing:
            raise NotFoundError(f"No shift override for employee {employee_id}")
        employee_shift_repository.delete_employee_shift(existing)
        db.session.commit()
        return {"message": f"Deleted employee shift override for {employee_id}"}
    except Exception:
        db.session.rollback()
        raise
