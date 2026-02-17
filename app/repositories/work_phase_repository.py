from app.con_sqlalchemy import WorkPhase, WorkAssignment, WorkPhaseBreak, bangkok_now
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


def get_work_phases_by_order_id(work_order_id):
    """Get all phases for a work order, ordered by work_phase_id (creation order)"""
    return WorkPhase.query.filter_by(work_order_id=work_order_id).order_by(WorkPhase.work_phase_id).all()


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


# --- Break Management ---

def create_break(work_phase_id, break_type=None):
    """Create a new break record (break_end is NULL = active break)"""
    from app.con_sqlalchemy import BreakType
    new_break = WorkPhaseBreak(
        work_phase_id=work_phase_id,
        break_start=bangkok_now(),
        break_type=break_type or BreakType.OTHER,
    )
    db.session.add(new_break)
    db.session.flush()
    return new_break


def get_active_break(work_phase_id):
    """Get the active (unclosed) break for a phase"""
    return WorkPhaseBreak.query.filter_by(
        work_phase_id=work_phase_id,
        break_end=None
    ).first()


def close_active_break(work_phase_id):
    """Close any active break by setting break_end to now"""
    active_break = get_active_break(work_phase_id)
    if active_break:
        active_break.break_end = bangkok_now()
        db.session.flush()
        return active_break
    return None
