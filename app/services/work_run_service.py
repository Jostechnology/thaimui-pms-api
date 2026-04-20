from app.con_sqlalchemy import WorkRun, WorkRunStatus, WorkRunReworkSource, WorkRunAssignment, WorkRunMachine, WorkRunBreak, BreakType, WorkOrderStatus, TestSessionStatus, TestResultStatus, bangkok_now, WorkRunRequiredItem, WorkRunPickingItem, AllocationMode
from app.repositories import work_run_repository, work_order_repository, test_result_repository, picking_request_repository, material_list_repository
from app.services import transaction_service, document_code_service, picking_allocation_service, work_order_service
from app.con_sqlalchemy import WorkRunTransactionType
from app.app import db
from app.exception import ManualRaiseToTest, NotFoundError, ValidationError, MissingFieldsError
from app.repositories import employee_salary_repository


def _apply_actuals_reverse_fifo(allocation_rows, qty_used_actual):
    """
    Distribute qty_used_actual across FIFO-ordered allocation rows.
    Releases leftover from the LAST rows first (reverse FIFO).
    Sets qty_consumed on each row.
    """
    total_allocated = sum(r.qty_allocated for r in allocation_rows)
    if qty_used_actual > total_allocated:
        for r in allocation_rows:
            r.qty_consumed = r.qty_allocated
        return
    to_release = total_allocated - qty_used_actual
    for r in reversed(allocation_rows):
        if to_release <= 0:
            r.qty_consumed = r.qty_allocated
        else:
            release_this = min(r.qty_allocated, to_release)
            r.qty_consumed = r.qty_allocated - release_this
            to_release -= release_this


def get_work_run_by_id(work_run_id):
    work_run = work_run_repository.get_work_run_display(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    return work_run


def get_work_runs_by_work_order(work_order_id):
    return work_run_repository.get_work_runs_by_work_order(work_order_id)


def get_work_runs_by_sales_item(sales_item_id):
    return work_run_repository.get_work_runs_by_sales_item(sales_item_id)


def create_work_run(work_order_id, data):
    """
    Create a new WorkRun on an existing WorkOrder. Newly created runs start as PENDING.

    Optional rework scenarios (mutually exclusive):

    A. Rework from production defects — supply `rework_sources`:
       [{"source_work_run_id": 1, "qty": 3}, ...]
       - Each source run must be COMPLETED and belong to this WorkOrder
       - qty per source <= that run's outstanding_defect_qty
       - sum(qty) must equal the new run's quantity

    B. Rework from test failures — supply `rework_source_test_result_id` + `qty_from_failed`:
       - TestResult must be COMPLETED with overall_status FAILED
       - qty_from_failed <= test_result.outstanding_failed_qty
       - qty_from_failed must equal the new run's quantity
    """
    work_order = work_order_repository.get_work_order_by_id(work_order_id)
    if not work_order:
        raise NotFoundError(f"Work Order {work_order_id} not found")

    rework_sources_data = data.get("rework_sources", [])
    rework_source_test_result_id = data.get("rework_source_test_result_id")

    if rework_sources_data and rework_source_test_result_id:
        raise ValidationError("ระบุได้เพียงแหล่งที่มาเดียว: rework_sources หรือ rework_source_test_result_id")

    quantity = data.get("quantity", 1)

    # --- Scenario A: rework from production defects ---
    if rework_sources_data:
        total_rework_qty = 0
        validated_sources = []

        for src in rework_sources_data:
            src_run_id = src.get("source_work_run_id")
            src_qty = src.get("qty")

            if not src_run_id:
                raise ValidationError("source_work_run_id ไม่ถูกต้อง")
            if not src_qty or src_qty <= 0:
                raise ValidationError(f"qty ของ source_work_run {src_run_id} ต้องมากกว่า 0")

            src_run = work_run_repository.get_work_run_by_id(src_run_id)
            if not src_run:
                raise NotFoundError(f"ไม่พบ WorkRun ID {src_run_id}")
            if src_run.status != WorkRunStatus.COMPLETED:
                raise ValidationError(f"WorkRun {src_run_id} ยังไม่เสร็จสิ้น (ต้องเป็น COMPLETED)")
            if src_run.work_order_id != work_order_id:
                raise ValidationError(f"WorkRun {src_run_id} ไม่ได้อยู่ใน WorkOrder นี้")
            if src_run.defect_qty is None or src_run.defect_qty == 0:
                raise ValidationError(f"WorkRun {src_run_id} ไม่มีของเสียที่สามารถ rework ได้")

            consumed = work_run_repository.get_consumed_defect_qty_for_work_run(src_run_id)
            outstanding = src_run.defect_qty - consumed
            if src_qty > outstanding:
                raise ValidationError(
                    f"WorkRun {src_run_id} มีของเสียคงเหลือ {outstanding} ชิ้น แต่ขอ rework {src_qty} ชิ้น"
                )

            total_rework_qty += src_qty
            validated_sources.append((src_run, src_qty))

        if total_rework_qty != quantity:
            raise ValidationError(
                f"ผลรวม qty ใน rework_sources ({total_rework_qty}) ต้องเท่ากับ quantity ของ WorkRun ({quantity})"
            )

        work_run = WorkRun(
            work_order_id=work_order_id,
            quantity=quantity,
            lot_number=document_code_service.generate_number("LOT"),
            wms_pick_reference=data.get("wms_pick_reference"),
            status=WorkRunStatus.PENDING,
        )
        work_run_repository.create_work_run(work_run)
        db.session.flush()

        for src_run, src_qty in validated_sources:
            db.session.add(WorkRunReworkSource(
                rework_work_run_id=work_run.work_run_id,
                source_work_run_id=src_run.work_run_id,
                qty=src_qty,
            ))
            transaction_service.create_work_run_transaction(
                src_run,
                WorkRunTransactionType.DEFECT_CONSUMED,
                src_qty,
                f"REWORK-{work_run.work_run_id}",
            )

    # --- Scenario B: rework from test failures ---
    elif rework_source_test_result_id:
        qty_from_failed = data.get("qty_from_failed")
        if not qty_from_failed or qty_from_failed <= 0:
            raise ValidationError("qty_from_failed ต้องมากกว่า 0")
        if qty_from_failed != quantity:
            raise ValidationError(
                f"quantity ({quantity}) ต้องเท่ากับ qty_from_failed ({qty_from_failed})"
            )

        test_result = test_result_repository.get_test_result_by_id(rework_source_test_result_id)
        if not test_result:
            raise NotFoundError(f"ไม่พบ TestResult ID {rework_source_test_result_id}")
        if test_result.session_status != TestSessionStatus.COMPLETED:
            raise ValidationError("TestResult ยังไม่เสร็จสิ้น (ต้องเป็น COMPLETED)")
        if test_result.overall_status != TestResultStatus.FAILED:
            raise ValidationError("TestResult ไม่ได้ FAILED จึงไม่สามารถ rework ได้")

        already_reworked = test_result_repository.get_reworked_qty_for_test_result(rework_source_test_result_id)
        outstanding_failed = test_result.failed_item_qty - already_reworked
        if qty_from_failed > outstanding_failed:
            raise ValidationError(
                f"TestResult {rework_source_test_result_id} มีของเสียคงเหลือ {outstanding_failed} ชิ้น แต่ขอ rework {qty_from_failed} ชิ้น"
            )

        work_run = WorkRun(
            work_order_id=work_order_id,
            quantity=quantity,
            lot_number=document_code_service.generate_number("LOT"),
            wms_pick_reference=data.get("wms_pick_reference"),
            status=WorkRunStatus.PENDING,
            rework_source_test_result_id=rework_source_test_result_id,
            qty_from_failed=qty_from_failed,
        )
        work_run_repository.create_work_run(work_run)

    # --- No rework source: regular new run ---
    else:
        work_run = WorkRun(
            work_order_id=work_order_id,
            quantity=quantity,
            lot_number=document_code_service.generate_number("LOT"),
            wms_pick_reference=data.get("wms_pick_reference"),
            status=WorkRunStatus.PENDING,
        )
        work_run_repository.create_work_run(work_run)

    db.session.flush()
    # _seed_required_items(work_run, work_order, rework_is_from_test=(rework_source_test_result_id is not None), rework_is_from_defect=bool(rework_sources_data))

    db.session.commit()
    return work_run


def _seed_required_items(work_run, work_order, rework_is_from_test=False, rework_is_from_defect=False):
    """
    Populate WorkRunRequiredItem from BOM (MaterialList) for regular runs.
    Rework runs start with an empty list — user adds extras via dedicated endpoint.
    """
    is_rework = rework_is_from_test or rework_is_from_defect
    if is_rework:
        return

    materials = material_list_repository.get_material_list_of_items([work_order.sales_item_id])
    for mat in materials:
        db.session.add(WorkRunRequiredItem(
            work_run_id=work_run.work_run_id,
            material_list_id=mat.material_list_id,
            item_code=mat.item_code,
            item_name=mat.item_name,
            quantity=mat.quantity,
            unit=mat.unit_name,
        ))


# --- Lifecycle ---

def start_work_run(work_run_id, data=None):
    """
    PENDING → INPROGRESS.
    Allocates picking items either by FIFO (auto) or operator-chosen (manual).

    data (optional):
        allocation_mode: "auto" (default) or "manual"
        material_sources: [{required_item_id, sources: [{picking_request_item_id, qty}]}]  — manual only
    """
    if data is None:
        data = {}

    allocation_mode_str = data.get("allocation_mode", "auto").upper()
    if allocation_mode_str not in ("AUTO", "MANUAL"):
        raise ValidationError(f"allocation_mode ไม่ถูกต้อง: {allocation_mode_str}")
    is_manual = allocation_mode_str == "MANUAL"
    mode_enum = AllocationMode.MANUAL if is_manual else AllocationMode.AUTO

    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status != WorkRunStatus.PENDING:
        raise ValidationError(f"Work Run must be PENDING to start (current: {work_run.status.value})")

    work_order = work_order_repository.get_work_order_by_id(work_run.work_order_id)
    if not work_order:
        raise NotFoundError(f"Work Order {work_run.work_order_id} not found")
    doc_entry = work_order.doc_entry

    required = work_run_repository.get_required_items(work_run_id)

    shortages = []
    all_allocations = []  # [(req, pri_id, qty)]

    if is_manual:
        manual_mat_sources = data.get("material_sources", [])
        mat_source_map = {ms["required_item_id"]: ms["sources"] for ms in manual_mat_sources}

    for req in required:
        if not req.material_list_id:
            continue
        if is_manual:
            sources = mat_source_map.get(req.id, [])
            if not sources:
                raise ValidationError(f"manual mode ต้องระบุ sources สำหรับ required item {req.id} ({req.item_code})")
            allocs = picking_allocation_service.allocate_manual(sources, req.quantity, req.item_code)
            all_allocations.extend((req, pri_id, qty) for pri_id, qty in allocs)
        else:
            candidates = picking_request_repository.get_available_picking_items_by_code(doc_entry, req.item_code)
            try:
                allocs = picking_allocation_service.allocate_fifo(candidates, req.quantity)
                all_allocations.extend((req, pri_id, qty) for pri_id, qty in allocs)
            except ValidationError:
                available_qty = sum(
                    max(0, pri.quantity - picking_request_repository.get_total_committed_qty(pri.picking_request_item_id))
                    for pri in candidates
                )
                shortages.append(f"\n{req.item_name} ({req.item_code}) ต้องการ {req.quantity} มีในคลัง {available_qty} \n")

    if shortages:
        raise ValidationError(
            f"วัตถุดิบในคลังไม่พอสำหรับการเริ่มผลิต: \n {', '.join(shortages)}"
        )

    for req, pri_id, qty in all_allocations:
        work_run_repository.create_picking_consumption(WorkRunPickingItem(
            work_run_id=work_run_id,
            picking_request_item_id=pri_id,
            work_run_required_item_id=req.id,
            qty_allocated=qty,
            allocation_mode=mode_enum,
        ))

    now = bangkok_now()
    work_run.status = WorkRunStatus.INPROGRESS
    work_run.start_date = now

    if work_order.status != WorkOrderStatus.INPROGRESS:
        work_order.status = WorkOrderStatus.INPROGRESS

    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


def pause_work_run(work_run_id, data):
    """INPROGRESS → PAUSED. Creates a WorkRunBreak with break_start=now."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status != WorkRunStatus.INPROGRESS:
        raise ValidationError(f"Work Run must be INPROGRESS to pause (current: {work_run.status.value})")

    break_type_str = data.get("break_type", "OTHER")
    try:
        break_type = BreakType(break_type_str)
    except ValueError:
        raise ValidationError(f"Invalid break_type: {break_type_str}")

    work_run.status = WorkRunStatus.PAUSED
    work_run_break = WorkRunBreak(
        work_run_id=work_run_id,
        break_type=break_type,
        remark=data.get("remark"),
    )
    work_run_repository.save_break(work_run_break)
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


def resume_work_run(work_run_id):
    """PAUSED → INPROGRESS. Closes the active break."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status != WorkRunStatus.PAUSED:
        raise ValidationError(f"Work Run must be PAUSED to resume (current: {work_run.status.value})")

    active_break = work_run_repository.get_active_break(work_run_id)
    if active_break:
        active_break.break_end = bangkok_now()

    work_run.status = WorkRunStatus.INPROGRESS
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


def complete_work_run(work_run_id, data):
    """
    Complete a WorkRun and record actual usable output.
    Run must be INPROGRESS or PAUSED (closes any open break automatically).

    Required in data:
    - usable_qty (int): how many items actually came out good
    - completion_remark (str): required when usable_qty < quantity (explains the defects)
    """
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status == WorkRunStatus.COMPLETED:
        raise ValidationError("Work Run is already completed")
    if work_run.status == WorkRunStatus.PENDING:
        raise ValidationError("Work Run has not been started yet")

    usable_qty = data.get("usable_qty")
    if usable_qty is None:
        raise ValidationError("กรุณากรอกจำนวนที่ผลิตสำเร็จ")
    if usable_qty < 0 or usable_qty > work_run.quantity:
        raise ValidationError(
            f"จำนวนที่ผลิตสำเร็จ ({usable_qty}) ต้องมากกว่า 0 และน้อยกว่าหรือเท่ากับจำนวนที่แพลนไว้ ({work_run.quantity})"
        )

    defect_qty = work_run.quantity - usable_qty
    if defect_qty > 0 and not data.get("completion_remark", "").strip():
        raise ValidationError("กรุณากรอกหมายเหตุ ในกรณีที่มีสินค้าผลิตผิดพลาด")

    now = bangkok_now()

    # Close open break if any
    active_break = work_run_repository.get_active_break(work_run_id)
    if active_break:
        active_break.break_end = now

    # Close open assignments
    for assignment in work_run_repository.get_open_assignments(work_run_id):
        assignment.to_time = now

    # Close open machines
    for machine_entry in work_run_repository.get_open_machines(work_run_id):
        machine_entry.to_time = now

    work_run.usable_qty = usable_qty
    work_run.completion_remark = data.get("completion_remark")
    work_run.status = WorkRunStatus.COMPLETED
    work_run.end_date = now

    # Apply material actuals — release leftover back to pool via reverse-FIFO
    material_actuals = data.get("material_actuals", [])
    reported_req_ids = set()
    for actual in material_actuals:
        req_id = actual.get("work_run_required_item_id")
        qty_used = actual.get("qty_used")
        if req_id is None or qty_used is None:
            continue
        if qty_used < 0:
            raise ValidationError(f"qty_used ต้องไม่ติดลบ (required_item {req_id})")

        req = work_run_repository.get_required_item_by_id(req_id)
        if not req or req.work_run_id != work_run_id:
            raise ValidationError(f"required_item {req_id} ไม่ได้อยู่ใน WorkRun นี้")

        req.qty_consumed_actual = qty_used
        allocation_rows = work_run_repository.get_wrpi_rows_for_required_item(req_id)
        _apply_actuals_reverse_fifo(allocation_rows, qty_used)
        reported_req_ids.add(req_id)

    # Rows not reported → default full consumption
    all_required = work_run_repository.get_required_items(work_run_id)
    for req in all_required:
        if req.id not in reported_req_ids:
            allocation_rows = work_run_repository.get_wrpi_rows_for_required_item(req.id)
            for r in allocation_rows:
                r.qty_consumed = r.qty_allocated

    db.session.commit()
    return work_run


# --- Worker assignment ---

def assign_employee(work_run_id, employee_id):
    """Open a new assignment for an employee on this work run."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status not in (WorkRunStatus.INPROGRESS, WorkRunStatus.PAUSED):
        raise ValidationError("Can only assign employees to an active work run (INPROGRESS or PAUSED)")

    existing = work_run_repository.get_open_assignment(work_run_id, employee_id)
    if existing:
        raise ValidationError(f"Employee {employee_id} already has an open assignment on this work run")

    assignment = WorkRunAssignment(
        work_run_id=work_run_id,
        employee_id=employee_id,
    )
    work_run_repository.save_assignment(assignment)
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


def unassign_employee(work_run_id, employee_id):
    """Close the open assignment for an employee."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")

    assignment = work_run_repository.get_open_assignment(work_run_id, employee_id)
    if not assignment:
        raise NotFoundError(f"Employee {employee_id} has no open assignment on Work Run {work_run_id}")

    assignment.to_time = bangkok_now()
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


# --- Machine assignment ---

def assign_machine(work_run_id, machine_id):
    """Open a new machine entry for this work run."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status not in (WorkRunStatus.INPROGRESS, WorkRunStatus.PAUSED):
        raise ValidationError("Can only assign machines to an active work run (INPROGRESS or PAUSED)")

    existing = work_run_repository.get_open_machine(work_run_id, machine_id)
    if existing:
        raise ValidationError(f"Machine {machine_id} is already assigned to this work run")

    machine_entry = WorkRunMachine(
        work_run_id=work_run_id,
        machine_id=machine_id,
    )
    work_run_repository.save_machine_entry(machine_entry)
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


def unassign_machine(work_run_id, machine_id):
    """Close the open machine entry."""
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")

    machine_entry = work_run_repository.get_open_machine(work_run_id, machine_id)
    if not machine_entry:
        raise NotFoundError(f"Machine {machine_id} has no open entry on Work Run {work_run_id}")

    machine_entry.to_time = bangkok_now()
    db.session.commit()
    return work_run_repository.get_work_run_display(work_run_id)


# --- Cost / detail ---

def get_work_run_detail(work_run_id):
    """
    Return a detailed cost breakdown for a work run.

    - Total work time (run duration minus breaks)
    - Per-employee labor cost (salary at creation date / 30 / 8 = hourly rate,
      multiplied by that employee's specific assignment duration)
    - Machine time summary
    """
    work_run = work_run_repository.get_work_run_display(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")

    now = bangkok_now()

    # Total run duration in seconds
    if work_run.start_date:
        end = work_run.end_date or now
        total_run_ms = max(0, (end - work_run.start_date).total_seconds() * 1000)
        # Subtract breaks
        break_ms = sum(
            max(0, ((b.break_end or now) - b.break_start).total_seconds() * 1000)
            for b in work_run.breaks
        )
        work_ms = max(0, total_run_ms - break_ms)
    else:
        work_ms = 0

    total_work_seconds = work_ms / 1000

    # Per-employee cost — use each employee's own assignment window
    employee_breakdown = []
    total_labor_cost = 0.0

    for assignment in work_run.assignments:
        emp = assignment.employee
        assign_end = assignment.to_time or now
        assign_seconds = max(0, (assign_end - assignment.from_time).total_seconds())

        salary = employee_salary_repository.get_salary_at_date(emp.employee_id, work_run.created_date)
        if salary is None:
            salary = emp.salary_base or 0.0

        hourly_rate = salary / 30 / 8 if salary > 0 else 0.0
        net_cost = round(hourly_rate * (assign_seconds / 3600), 2)
        total_labor_cost += net_cost

        employee_breakdown.append({
            "employee_id": emp.employee_id,
            "employee_first_name": emp.employee_first_name,
            "employee_last_name": emp.employee_last_name,
            "status": emp.status.value if hasattr(emp.status, "value") else str(emp.status),
            "salary_at_run": salary,
            "hourly_rate": round(hourly_rate, 2),
            "from_time": assignment.from_time.isoformat() if assignment.from_time else None,
            "to_time": assignment.to_time.isoformat() if assignment.to_time else None,
            "time_spent_seconds": round(assign_seconds, 2),
            "net_cost": net_cost,
        })

    # Machine time summary
    machine_breakdown = []
    for me in work_run.machines:
        machine_end = me.to_time or now
        machine_seconds = max(0, (machine_end - me.from_time).total_seconds())
        machine_breakdown.append({
            "machine_id": me.machine_id,
            "machine_name": me.machine.machine_name if me.machine else None,
            "from_time": me.from_time.isoformat() if me.from_time else None,
            "to_time": me.to_time.isoformat() if me.to_time else None,
            "time_spent_seconds": round(machine_seconds, 2),
        })

    breaks_data = [
        {
            "break_id": b.break_id,
            "break_start": b.break_start.isoformat() if b.break_start else None,
            "break_end": b.break_end.isoformat() if b.break_end else None,
            "break_type": b.break_type.value if hasattr(b.break_type, "value") else str(b.break_type),
            "remark": b.remark,
        }
        for b in work_run.breaks
    ]

    return {
        "work_run_id": work_run.work_run_id,
        "lot_number": work_run.lot_number,
        "status": work_run.status.value if hasattr(work_run.status, "value") else str(work_run.status),
        "start_date": work_run.start_date.isoformat() if work_run.start_date else None,
        "end_date": work_run.end_date.isoformat() if work_run.end_date else None,
        "total_work_seconds": round(total_work_seconds, 2),
        "total_labor_cost": round(total_labor_cost, 2),
        "employee_breakdown": employee_breakdown,
        "machine_breakdown": machine_breakdown,
        "breaks": breaks_data,
    }


# --- Required items (rework extras) ---

def add_required_item(work_run_id, items):
    """
    Add extra material requirements to a PENDING rework WorkRun.
    Accepts a list of items. Regular runs are seeded from BOM at creation.
    """
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status != WorkRunStatus.PENDING:
        raise ValidationError("วัตถุดิบเพิ่มเติมเพิ่มได้เฉพาะตอน PENDING")

    for i, data in enumerate(items):
        item_code = (data.get("item_code") or "").strip()
        item_name = (data.get("item_name") or "").strip()
        quantity = data.get("quantity")

        if not item_code:
            raise ValidationError(f"item[{i}]: item_code ต้องระบุ")
        if not item_name:
            raise ValidationError(f"item[{i}]: item_name ต้องระบุ")
        if not quantity or quantity <= 0:
            raise ValidationError(f"item[{i}]: quantity ต้องมากกว่า 0")

        req = WorkRunRequiredItem(
            work_run_id=work_run_id,
            material_list_id=data.get("material_list_id"),
            item_code=item_code,
            item_name=item_name,
            quantity=quantity,
            unit=data.get("unit"),
        )
        work_run_repository.create_required_item(req)

    db.session.commit()
    return work_run_repository.get_required_items(work_run_id)


def get_required_items(work_run_id):
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    return work_run_repository.get_required_items(work_run_id)

def update_required_item(required_item_id, data):
    quantity = data.get("quantity")
    if quantity is None or quantity <= 0:
        raise ValidationError("quantity ต้องมากกว่า 0")
    req = work_run_repository.get_required_item_by_id(required_item_id)
    if not req:
        raise NotFoundError(f"Required item {required_item_id} not found")
    req.quantity = quantity
    db.session.commit()
    return req


def get_pick_requests_for_work_run(work_run_id):
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    work_order = work_order_repository.get_work_order_by_id(work_run.work_order_id)
    if not work_order:
        raise NotFoundError(f"Work Order {work_run.work_order_id} not found")
    required = work_run_repository.get_required_items(work_run_id)
    item_codes = list({r.item_code for r in required if r.item_code})
    if not item_codes:
        return []
    return picking_request_repository.get_available_pick_requests_by_codes(
        work_order.doc_entry, item_codes
    )


def get_material_using_in_work_order_of_work_run(work_run_id):
    try:
        work_run = work_run_repository.get_work_run_by_id(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")
        
        work_order_id = work_run.work_order_id
        work_order = work_order_service.get_work_order_by_id(work_order_id)
        if not work_order:
            raise NotFoundError(f"Work Order {work_order_id} not found")
        
        materials = material_list_repository.get_material_list_of_items([work_order.sales_item_id])
        return materials
    except Exception:
        raise
