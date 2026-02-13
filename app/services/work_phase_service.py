from app.con_sqlalchemy import WorkPhase, WorkAssignment
from app.ma_sqlalchemy import WorkPhaseSchema
from app.repositories import work_phase_repository
from app.app import db


def create_work_phase(data):
    try:
        work_phases = []
        for item in data.get("items", []):
            work_phase = WorkPhase(
                work_order_id=item.get("work_order_id"),
                phase_name=item.get("phase_name"),
                start_date=item.get("start_date"),
            )
            work_phase = work_phase_repository.create_work_phase(work_phase)
            for employee_id in item.get("employee_id_list", []):
                assignment = WorkAssignment(
                    work_phase_id=work_phase.work_phase_id,
                    employee_id=employee_id,
                )
                work_phase_repository.create_work_assignment(assignment)
            work_phases.append(work_phase)
        db.session.commit()
        return WorkPhaseSchema(many=True).dump(work_phases)
    except Exception:
        db.session.rollback()
        raise


def update_work_phase(work_phase_id, data):
    try:
        work_phase = work_phase_repository.get_work_phase_by_id(work_phase_id)
        if not work_phase:
            raise Exception("Work phase not found")

        if "phase_status" in data:
            work_phase.phase_status = data["phase_status"]

        if "end_date" in data:
            work_phase.end_date = data["end_date"]

        if "employee_id_list" in data:
            work_phase_repository.delete_work_assignments_by_phase(work_phase_id)
            for employee_id in data["employee_id_list"]:
                assignment = WorkAssignment(
                    work_phase_id=work_phase_id,
                    employee_id=employee_id,
                )
                work_phase_repository.create_work_assignment(assignment)

        work_phase = work_phase_repository.update_work_phase(work_phase)
        db.session.commit()
        return WorkPhaseSchema().dump(work_phase)
    except Exception:
        db.session.rollback()
        raise
