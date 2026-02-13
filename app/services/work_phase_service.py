from app.ma_sqlalchemy import WorkPhaseSchema
from app.repositories import work_phase_repository


def create_work_phase(data):
    try:
        items = data.get("items", [])
        work_phases = work_phase_repository.create_work_phase(items)
        return WorkPhaseSchema(many=True).dump(work_phases)
    except Exception:
        raise



def delete_work_phase(work_phase_id):
    try:
        work_phase_repository.delete_work_phase(work_phase_id)
        return {"message": "Work phase deleted successfully"}
    except Exception:
        raise
