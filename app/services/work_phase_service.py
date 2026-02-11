from app.ma_sqlalchemy import WorkPhaseSchema
from app.repositories import work_phase_repository


def create_work_phase(data):
    try:
        work_phase = work_phase_repository.create_work_phase(data)
        return WorkPhaseSchema().dump(work_phase)
    except Exception:
        raise