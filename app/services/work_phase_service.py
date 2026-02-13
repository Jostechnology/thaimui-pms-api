from app.ma_sqlalchemy import WorkPhaseSchema
from app.repositories import work_phase_repository


def create_work_phase(data):
    try:
        items = data.get("items", [])
        work_phases = work_phase_repository.create_work_phase(items)
        return WorkPhaseSchema(many=True).dump(work_phases)
    except Exception:
        raise

def edit_work_phase(work_phase_id, data):
    try:
        work_phase = work_phase_repository.edit_work_phase(work_phase_id, data)
        return WorkPhaseSchema().dump(work_phase)
    except Exception:
        raise

def update_phase_status(work_phase_id, data):
    try:
        new_status = data.get("phase_status")
        if not new_status:
            raise ValueError("phase_status is required")
        work_phase = work_phase_repository.update_phase_status(work_phase_id, new_status)
        return WorkPhaseSchema().dump(work_phase)
    except Exception:
        raise

def delete_work_phase(work_phase_ids):
    try:
        result = work_phase_repository.delete_work_phase(work_phase_ids)
        return result
    except Exception:
        raise
