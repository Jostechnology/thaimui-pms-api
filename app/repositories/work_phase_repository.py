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


def delete_work_phase(work_phase_id):
    try:
        work_phase = WorkPhase.query.get(work_phase_id)
        if not work_phase:
            raise Exception("Work phase not found")

        # Delete related WorkAssignments first
        WorkAssignment.query.filter_by(work_phase_id=work_phase_id).delete()
        db.session.delete(work_phase)
        db.session.commit()
        return {"message": "Work phase deleted successfully"}
    except Exception:
        db.session.rollback()
        raise