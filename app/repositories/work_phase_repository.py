from app.con_sqlalchemy import WorkPhase, WorkAssignment, WorkPhaseBreak, bangkok_now, BreakType
from app.app import db


def save_work_phase(work_phase):
    try:
        db.session.add(work_phase)
    except Exception:
        db.session.rollback()
        raise

def delete_all_work_assignments(work_assignments):
    try:
        for assignment in work_assignments:
            db.session.delete(assignment)
    except Exception:
        db.session.rollback()
        raise
def save_work_assignment(assignment):
    try:
        db.session.add(assignment)
    except Exception:
        db.session.rollback()
        raise
def save_all_work_assignments(assignments):
    try:
        db.session.add_all(assignments)
    except Exception:
        db.session.rollback()
        raise

def get_work_phase_by_id(work_phase_id):
    return WorkPhase.query.get(work_phase_id)


def get_work_phases_by_order_id(work_order_id):
    """Get all phases for a work order, ordered by work_phase_id (creation order)"""
    return WorkPhase.query.filter_by(work_order_id=work_order_id).order_by(WorkPhase.work_phase_id).all()


def get_work_assignments_by_phase(work_phase_id):
    return WorkAssignment.query.filter_by(work_phase_id=work_phase_id).all()


def delete_work_phase(work_phase_ids):
    try:
        delete_count = (
            WorkPhase.query.filter(WorkPhase.work_phase_id.in_(work_phase_ids)).delete(synchronize_session=False)
        )
        return delete_count
    except Exception:
        db.session.rollback()
        raise


# --- Break Management ---

def save_break(work_phase_break):
    try:
        db.session.add(work_phase_break)
        return work_phase_break
    except Exception:
        db.session.rollback()
        raise


def get_active_break(work_phase_id):
    """Get the active (unclosed) break for a phase"""
    return WorkPhaseBreak.query.filter_by(
        work_phase_id=work_phase_id,
        break_end=None
    ).first()

