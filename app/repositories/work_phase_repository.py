from app.con_sqlalchemy import WorkPhase, WorkAssignment, VALID_PHASE_STATUSES
from app.app import db


def create_work_phase(items):
    try:
        work_phases = []
        for data in items:
            work_phase = WorkPhase(
                work_order_id=data.get("work_order_id"),
                phase_name=data.get("phase_name"),
                start_date=data.get("start_date"),
            )
            db.session.add(work_phase)
            db.session.flush()  # get work_phase_id before committing
            # Create WorkAssignment for each employee
            employee_id_list = data.get("employee_id_list", [])
            for employee_id in employee_id_list:
                assignment = WorkAssignment(
                    work_phase_id=work_phase.work_phase_id,
                    employee_id=employee_id,
                )
                db.session.add(assignment)

            work_phases.append(work_phase)

        db.session.commit()
        return work_phases
    except Exception:
        db.session.rollback()
        raise


def edit_work_phase(work_phase_id, data):
    try:
        work_phase = WorkPhase.query.get(work_phase_id)
        if not work_phase:
            raise Exception("Work phase not found")

        work_phase.phase_name = data.get("phase_name", work_phase.phase_name)
        work_phase.start_date = data.get("start_date", work_phase.start_date)

        # Update phase_status if provided — validate against allowed values
        if "phase_status" in data:
            incoming = data.get("phase_status")
            if incoming not in VALID_PHASE_STATUSES:
                raise ValueError(f"Invalid phase_status '{incoming}'. Must be one of: {', '.join(VALID_PHASE_STATUSES)}")
            work_phase.phase_status = incoming

        # Update WorkAssignment
        employee_id_list = data.get("employee_id_list", [])
        existing_assignments = WorkAssignment.query.filter_by(work_phase_id=work_phase_id).all()
        existing_employee_ids = {assignment.employee_id for assignment in existing_assignments}

        # Add new assignments
        for employee_id in employee_id_list:
            if employee_id not in existing_employee_ids:
                new_assignment = WorkAssignment(
                    work_phase_id=work_phase_id,
                    employee_id=employee_id,
                )
                db.session.add(new_assignment)

        # Remove old assignments
        for assignment in existing_assignments:
            if assignment.employee_id not in employee_id_list:
                db.session.delete(assignment)

        db.session.commit()
        return work_phase
    except Exception:
        db.session.rollback()
        raise


def update_phase_status(work_phase_id, new_status):
    try:
        work_phase = WorkPhase.query.get(work_phase_id)
        if not work_phase:
            raise Exception("Work phase not found")

        if new_status not in VALID_PHASE_STATUSES:
            raise ValueError(f"Invalid phase_status '{new_status}'. Must be one of: {', '.join(VALID_PHASE_STATUSES)}")

        work_phase.phase_status = new_status
        db.session.commit()
        return work_phase
    except Exception:
        db.session.rollback()
        raise


def create_work_assignment(assignment):
    try:
        db.session.add(assignment)
        db.session.flush()
        return assignment
    except Exception:
        db.session.rollback()
        raise


def get_work_phase_by_id(work_phase_id):
    return WorkPhase.query.get(work_phase_id)


def delete_work_assignments_by_phase(work_phase_id):
    try:
        WorkAssignment.query.filter_by(work_phase_id=work_phase_id).delete()
        db.session.flush()
    except Exception:
        db.session.rollback()
        raise


def delete_work_phase(work_phase_ids):
    try:
        for work_phase_id in work_phase_ids:
            work_phase = WorkPhase.query.get(work_phase_id)
            if not work_phase:
                raise Exception(f"Work phase id {work_phase_id} not found")

            # Clear relationship first to avoid StaleDataError
            work_phase.employee_list.clear()
            db.session.delete(work_phase)

        db.session.commit()
        return {"message": f"Deleted {len(work_phase_ids)} work phase(s) successfully"}
    except Exception:
        db.session.rollback()
        raise