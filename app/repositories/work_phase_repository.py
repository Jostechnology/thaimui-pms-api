from app.con_sqlalchemy import WorkPhase, WorkAssignment, WorkItem
from app.app import db


def create_work_phase(data):
    try:
        work_phase = WorkPhase(
            work_order_id=data.get("work_order_id"),
            phase_name=data.get("phase_name"),
            start_date=data.get("start_date"),
        )
        db.session.add(work_phase)
        db.session.flush()  # get work_phase_id before committing
        work_phase.work_order.current_phase_id = work_phase.work_phase_id
        # Create WorkAssignment for each employee
        employee_id_list = data.get("employee_id_list", [])
        for employee_id in employee_id_list:
            assignment = WorkAssignment(
                work_phase_id=work_phase.work_phase_id,
                employee_id=employee_id,
            )
            db.session.add(assignment)

        # Create WorkItem for each sales item
        sales_item_id_list = data.get("sales_item_id_list", [])
        for sales_item_id in sales_item_id_list:
            work_item = WorkItem(
                work_phase_id=work_phase.work_phase_id,
                sales_item_id=sales_item_id,
            )
            db.session.add(work_item)

        db.session.commit()
        return work_phase
    except Exception:
        db.session.rollback()
        raise
