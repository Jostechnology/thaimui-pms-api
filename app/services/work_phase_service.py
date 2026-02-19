from app.con_sqlalchemy import PhaseStatus, WorkOrderStatus, WorkPhase, WorkAssignment, BreakType, WorkPhaseBreak, bangkok_now
from app.ma_sqlalchemy import WorkPhaseSchema, WorkOrderSchema
from app.repositories import work_order_repository, work_phase_repository
from app.app import db
from app.exception import MissingFieldsError, NotFoundError


def create_work_phase(data):
    try:
        work_phases = []
        items = data.get("items", [])
        work_order_id = items[0].get("work_order_id") if items else None
        for item in items:
            work_phase = WorkPhase(
                work_order_id=work_order_id,
                phase_name=item.get("phase_name"),
            )
            work_phase_repository.save_work_phase(work_phase)
            if item.get("employee_id_list") == [] or item.get("employee_id_list") is None:
                raise MissingFieldsError("employee_id_list is required for creating work phase assignments")
            for employee_id in item.get("employee_id_list", []):
                assignment = WorkAssignment(
                    work_phase = work_phase,
                    employee_id=employee_id,
                )
                work_phase_repository.save_work_assignment(assignment)
            work_phases.append(work_phase)
        db.session.commit()
        return WorkPhaseSchema(many=True).dump(work_phases)
    except Exception:
        db.session.rollback()
        raise


def update_work_phase(data):
    try:
        results = []
        first_work_phase_id = data.get("items", [{}])[0].get("work_phase_id")
        first_work_phase = work_phase_repository.get_work_phase_by_id(first_work_phase_id)
        work_order_id = first_work_phase.work_order_id if first_work_phase else None
        work_order = work_order_repository.get_work_order_by_id(work_order_id)
        for item in data.get("items", []):
            work_phase_id = item.get("work_phase_id")
            work_phase = work_phase_repository.get_work_phase_by_id(work_phase_id)
            if work_phase.phase_status == PhaseStatus.เสร็จสิ้น:
                raise ValueError(f"Cannot update completed work phase id {work_phase_id}")
            if not work_phase:
                raise NotFoundError(f"Work phase id {work_phase_id} not found")
            
            if "phase_name" in item:
                work_phase.phase_name = item["phase_name"]

            # --- Status transition with Pause/Resume logic ---
            if "phase_status" in item:
                new_status = item["phase_status"]
                current_status = work_phase.phase_status
                break_type_str = item.get("break_type", "พักเบรค")
                if new_status == "กําลังดําเนินการ" :
                    new_status = PhaseStatus.กำลังดําเนินการ
                elif new_status == "รอดําเนินการ" :
                    new_status = PhaseStatus.รอดําเนินการ
                else:
                    new_status = PhaseStatus(new_status)
                now = bangkok_now()
                if current_status == PhaseStatus.รอดําเนินการ and new_status == PhaseStatus.กำลังดําเนินการ:
                    work_phase.phase_status = PhaseStatus.กำลังดําเนินการ
                    work_phase.start_date = now
                    work_phase.start_date = now
                    work_order.current_phase = work_phase
                    work_order.status = WorkOrderStatus.กำลังดําเนินการ
                
                elif current_status == PhaseStatus.กำลังดําเนินการ and new_status == PhaseStatus.หยุดชั่วคราว:
                    work_phase.phase_status = PhaseStatus.หยุดชั่วคราว
                    work_phase_break = WorkPhaseBreak(
                        work_phase_id=work_phase_id,
                        break_start=now,
                        break_type=BreakType(break_type_str)
                    )
                    
                    work_phase_repository.save_break(work_phase_break)

                elif current_status == PhaseStatus.หยุดชั่วคราว and new_status == PhaseStatus.กำลังดําเนินการ:
                    work_phase.phase_status = PhaseStatus.กำลังดําเนินการ
                    stop_break(work_phase_id)

                elif new_status == PhaseStatus.เสร็จสิ้น:
                    work_phase.phase_status = PhaseStatus.เสร็จสิ้น
                    work_phase.end_date = now
                    stop_break(work_phase_id)

                else:
                    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
                    work_phase.phase_status = new_status
            if "employee_id_list" in item:
                new_employee_ids = set(item["employee_id_list"])
                existing_assignments = work_phase_repository.get_work_assignments_by_phase(work_phase_id)

                # ลบ assignment ที่ employee_id ไม่อยู่ในรายการใหม่
                delete_work_assignments = [a for a in existing_assignments if a.employee_id not in new_employee_ids]
                # เพิ่ม assignment สำหรับ employee_id ใหม่ที่ยังไม่มี
                existing_employee_ids = set(a.employee_id for a in existing_assignments)
                create_work_assignments = [
                    WorkAssignment(work_phase=work_phase, employee_id=eid)
                    for eid in new_employee_ids if eid not in existing_employee_ids
                ]

                work_phase_repository.save_all_work_assignments(create_work_assignments)
                work_phase_repository.delete_all_work_assignments(delete_work_assignments)
                work_phase = work_phase_repository.save_work_phase(work_phase)
                results.append(work_phase)

        db.session.commit()
        return WorkPhaseSchema(many=True).dump(results)
    except Exception:
        db.session.rollback()
        raise


def delete_work_phase(work_phase_ids):
    try:
        if not work_phase_ids:
            raise ValueError("work_phase_ids list cannot be empty")
        work_phase = work_phase_repository.get_work_phase_by_id(work_phase_ids[0])
        if not work_phase:
                raise Exception(f"Work phase id {wp_id} not found")
        for wp_id in work_phase_ids:
            if work_phase.phase_status == "เสร็จสิ้น":
                raise ValueError(f"Cannot delete completed work phase id {wp_id}")
        result = work_phase_repository.delete_work_phase(work_phase_ids)
        db.session.commit()
        return result
    except Exception:
        db.session.rollback()
        raise

def stop_break(work_phase_id):
    try:
        active_break = work_phase_repository.get_active_break(work_phase_id)
        if active_break:
            active_break.break_end = bangkok_now()
            work_phase_repository.save_break(active_break)
    except Exception:
        db.session.rollback()
        raise