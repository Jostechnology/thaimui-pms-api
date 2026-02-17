from app.con_sqlalchemy import WorkPhase, WorkAssignment, BreakType, bangkok_now
from app.ma_sqlalchemy import WorkPhaseSchema, WorkOrderSchema
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

            # --- Status transition with Pause/Resume logic ---
            if "phase_status" in item:
                new_status = item["phase_status"]
                current_status = work_phase.phase_status
                break_type_str = item.get("break_type", "Other")

                # Validate transition
                allowed = VALID_TRANSITIONS.get(current_status, [])
                if new_status not in allowed:
                    raise ValueError(
                        f"Cannot transition from '{current_status}' to '{new_status}'. "
                        f"Allowed: {allowed}"
                    )

                now = bangkok_now()

                if current_status == "Pending" and new_status == "InProgress":
                    work_phase.phase_status = "InProgress"
                    work_phase.start_date = now

                elif current_status == "InProgress" and new_status == "Paused":
                    work_phase.phase_status = "Paused"
                    bt = _parse_break_type(break_type_str)
                    work_phase_repository.create_break(work_phase_id, bt)

                elif current_status == "Paused" and new_status == "InProgress":
                    work_phase.phase_status = "InProgress"
                    work_phase_repository.close_active_break(work_phase_id)

                elif new_status == "Completed":
                    work_phase.phase_status = "Completed"
                    work_phase.end_date = now
                    work_phase_repository.close_active_break(work_phase_id)
                    _advance_next_phase(work_phase)

                else:
                    work_phase.phase_status = new_status

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

        # Update current_phase pointer for affected work orders
        updated_order_ids = set(r.work_order_id for r in results)
        for order_id in updated_order_ids:
            _update_current_phase(order_id)

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


# ====================================================
# Status Update Logic (Sequential + Pause/Resume)
# ====================================================

# Valid transitions map
VALID_TRANSITIONS = {
    "Pending":     ["InProgress"],
    "InProgress":  ["Paused", "Completed"],
    "Paused":      ["InProgress", "Completed"],
    "Completed":   [],        # Terminal state — no going back
    "Cancel":      [],
}


def update_work_phase_status(data):
    """
    Update a work phase status with full Sequential + Pause/Resume logic.
    
    Accepts:
        work_phase_id: int
        new_status: str ("InProgress" | "Paused" | "Completed")
        break_type: str (optional, for pause: "Lunch" | "Short Break" | "Other")
    
    Logic:
        Pending → InProgress:  set start_date = now
        InProgress → Paused:   create a new break record (break_end = NULL)
        Paused → InProgress:   close the active break (break_end = now)
        InProgress → Completed: set end_date = now, close any active break,
                                 auto-advance next phase to InProgress
        Paused → Completed:    close active break, set end_date = now,
                               auto-advance next phase to InProgress
    """
    try:
        work_phase_id = data.get("work_phase_id")
        new_status = data.get("new_status")
        break_type_str = data.get("break_type", "Other")

        # 1. Validate input
        if not work_phase_id or not new_status:
            raise ValueError("work_phase_id and new_status are required")

        work_phase = work_phase_repository.get_work_phase_by_id(work_phase_id)
        if not work_phase:
            raise Exception(f"Work phase id {work_phase_id} not found")

        current_status = work_phase.phase_status

        # 2. Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{current_status}' to '{new_status}'. "
                f"Allowed: {allowed}"
            )

        now = bangkok_now()

        # 3. Execute transition logic
        if current_status == "Pending" and new_status == "InProgress":
            # Start working — set start_date
            work_phase.phase_status = "InProgress"
            work_phase.start_date = now

        elif current_status == "InProgress" and new_status == "Paused":
            # Pause — create a break record
            work_phase.phase_status = "Paused"
            bt = _parse_break_type(break_type_str)
            work_phase_repository.create_break(work_phase_id, bt)

        elif current_status == "Paused" and new_status == "InProgress":
            # Resume — close the active break
            work_phase.phase_status = "InProgress"
            work_phase_repository.close_active_break(work_phase_id)

        elif new_status == "Completed":
            # Complete — close any active break, set end_date, advance next phase
            work_phase.phase_status = "Completed"
            work_phase.end_date = now
            work_phase_repository.close_active_break(work_phase_id)
            _advance_next_phase(work_phase)

        work_phase_repository.update_work_phase(work_phase)

        # 4. Update work order's current_phase pointer
        _update_current_phase(work_phase.work_order_id)

        db.session.commit()

        # Return updated work order data
        work_order = work_order_repository.get_work_order_by_id(work_phase.work_order_id)
        return WorkOrderSchema().dump(work_order)

    except Exception:
        db.session.rollback()
        raise


def _advance_next_phase(completed_phase):
    """When a phase is completed, auto-start the next Pending phase"""
    all_phases = work_phase_repository.get_work_phases_by_order_id(completed_phase.work_order_id)
    
    found_completed = False
    for phase in all_phases:
        if phase.work_phase_id == completed_phase.work_phase_id:
            found_completed = True
            continue
        if found_completed and phase.phase_status == "Pending":
            phase.phase_status = "InProgress"
            phase.start_date = bangkok_now()
            work_phase_repository.update_work_phase(phase)
            return  # Only advance one phase

    # If no more Pending phases, check if all are completed
    all_completed = all(p.phase_status == "Completed" for p in all_phases)
    if all_completed:
        # Update work order status to completed
        work_order = work_order_repository.get_work_order_by_id(completed_phase.work_order_id)
        work_order.status = "Completed"


def _update_current_phase(work_order_id):
    """Update the work order's current_phase_id to the active (InProgress/Paused) phase"""
    all_phases = work_phase_repository.get_work_phases_by_order_id(work_order_id)
    work_order = work_order_repository.get_work_order_by_id(work_order_id)
    
    # Find the active phase (InProgress or Paused)
    active_phase = None
    for phase in all_phases:
        if phase.phase_status in ("InProgress", "Paused"):
            active_phase = phase
            break
    
    if active_phase:
        work_order.current_phase_id = active_phase.work_phase_id
    else:
        # No active phase — might be all completed or all pending
        work_order.current_phase_id = None


def _parse_break_type(break_type_str):
    """Convert string to BreakType enum"""
    mapping = {
        "Lunch": BreakType.LUNCH,
        "Short Break": BreakType.SHORT_BREAK,
        "Other": BreakType.OTHER,
    }
    return mapping.get(break_type_str, BreakType.OTHER)
