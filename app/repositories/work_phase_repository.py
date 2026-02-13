from app.con_sqlalchemy import WorkPhase, WorkAssignment
from app.app import db


def create_work_phase(work_phase):
    try:
        db.session.add(work_phase)
        db.session.flush()
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


def update_work_phase(work_phase):
    try:
        db.session.flush()
        db.session.refresh(work_phase)
        return work_phase
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