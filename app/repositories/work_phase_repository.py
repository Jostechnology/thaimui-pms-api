from app.con_sqlalchemy import WorkPhase, WorkAssignment, WorkPhaseBreak, bangkok_now, BreakType, PhaseStatus
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
    query = db.session.query(WorkPhase).filter(WorkPhase.work_phase_id == work_phase_id)
    return query.first()


def get_work_phases_by_run_id(work_run_id):
    """Get all phases for a work run, ordered by work_phase_id (creation order)"""
    query = db.session.query(WorkPhase).filter(WorkPhase.work_run_id == work_run_id).order_by(WorkPhase.work_phase_id)
    return query.all()


def has_unfinished_phases_for_work_run(work_run_id):
    query = db.session.query(WorkPhase).filter(
        WorkPhase.work_run_id == work_run_id,
        WorkPhase.phase_status != PhaseStatus.COMPLETED
    )
    return query.first() is not None


def get_work_assignments_by_phase(work_phase_id):
    query = db.session.query(WorkAssignment).filter(WorkAssignment.work_phase_id == work_phase_id)
    return query.all()


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

