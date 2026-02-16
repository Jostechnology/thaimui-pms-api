from app.con_sqlalchemy import WorkPhase, WorkAssignment
from app.ma_sqlalchemy import WorkPhaseSchema
from app.repositories import work_order_repository, work_phase_repository
from app.app import db


def create_work_phase(data):
    try:
        work_phases = []
        items = data.get("items", [])
        work_order_id = items[0].get("work_order_id") if items else None
        work_order = work_order_repository.get_work_order_by_id(work_order_id)
        work_order.status = "Working"
        for item in items:
            work_phase = WorkPhase(
                work_order_id=work_order_id,
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


def update_work_phase(data):
    try:
        results = []
        for item in data.get("items", []):
            work_phase_id = item.get("work_phase_id")
            work_phase = work_phase_repository.get_work_phase_by_id(work_phase_id)
            if not work_phase:
                raise Exception(f"Work phase id {work_phase_id} not found")
            
            if "phase_name" in item:
                work_phase.phase_name = item["phase_name"]

            if "phase_status" in item:
                work_phase.phase_status = item["phase_status"]

            if "end_date" in item:
                work_phase.end_date = item["end_date"]

            if "employee_id_list" in item:
                work_phase_repository.delete_work_assignments_by_phase(work_phase_id)
                for employee_id in item["employee_id_list"]:
                    assignment = WorkAssignment(
                        work_phase_id=work_phase_id,
                        employee_id=employee_id,
                    )
                    work_phase_repository.create_work_assignment(assignment)

            work_phase = work_phase_repository.update_work_phase(work_phase)
            results.append(work_phase)

        db.session.commit()
        return WorkPhaseSchema(many=True).dump(results)
    except Exception:
        db.session.rollback()
        raise


def delete_work_phase(work_phase_ids):
    try:
        result = work_phase_repository.delete_work_phase(work_phase_ids)
        return result
    except Exception:
        raise
