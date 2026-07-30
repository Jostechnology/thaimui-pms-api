import logging
from app.con_sqlalchemy import WorkRun, WorkRunStatus, WorkRunReworkSource, WorkRunAssignment, WorkRunMachine, WorkRunCost, WorkRunBreak, BreakType, WorkOrderStatus, TestSessionStatus, TestResultStatus, bangkok_now, WorkRunRequiredItem
from app.repositories import work_run_repository, work_order_repository, test_result_repository, picking_request_repository, material_list_repository
from app.services import transaction_service, document_code_service, work_order_service
from app.con_sqlalchemy import WorkRunTransactionType
from app.app import db
from app.exception import ManualRaiseToTest, NotFoundError, ValidationError, MissingFieldsError
from app.utils import QTY_EPS, qty_equal
from app.repositories import employee_salary_repository
from app.services import labor_cost_service

logger = logging.getLogger(__name__)


def _to_naive(dt):
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _calc_depreciation_per_second(machine) -> float:
    if not all([machine.purchase_price, machine.useful_life_years, machine.working_hours_per_day]):
        return 0.0
    total_seconds = machine.useful_life_years * 365 * machine.working_hours_per_day * 3600
    if total_seconds <= 0:
        return 0.0
    return machine.purchase_price / total_seconds


def _calc_maintenance_rate_per_second(machine) -> float:
    remaining = machine.remaining_maintenance_cost or 0
    if remaining <= 0:
        return 0.0

    past_entries = db.session.query(WorkRunMachine).filter(
        WorkRunMachine.machine_id == machine.machine_id,
        WorkRunMachine.to_time.isnot(None),
    ).all()

    history_seconds = sum(
        max(0, (_to_naive(e.to_time) - _to_naive(e.from_time)).total_seconds())
        for e in past_entries
        if e.from_time and e.to_time
    )

    if machine.is_second_hand and (machine.accumulated_hours or 0) > 0:
        total_past_seconds = history_seconds + (machine.accumulated_hours * 3600)
    else:
        total_past_seconds = history_seconds

    if total_past_seconds <= 0:
        return 0.0

    return remaining / total_past_seconds


def _create_machine_cost_record(machine_entry, machine):
    """Store cost rates directly on the WorkRunMachine entry."""
    machine_entry.depreciation_per_second = _calc_depreciation_per_second(machine)
    machine_entry.maintenance_rate_per_second = _calc_maintenance_rate_per_second(machine)


def _allocate_and_finalize_machine_cost(machine_entry, breaks):
    """Compute and store finalized cost on WorkRunMachine when it is closed."""
    from app.con_sqlalchemy import Machine
    machine = db.session.query(Machine).filter(Machine.machine_id == machine_entry.machine_id).first()
    if not machine:
        return

    mStart = _to_naive(machine_entry.from_time)
    mEnd = _to_naive(machine_entry.to_time)
    total_seconds = max(0, (mEnd - mStart).total_seconds())
    break_seconds = sum(
        max(0, (min(_to_naive(b.break_end or machine_entry.to_time), mEnd)
                - max(_to_naive(b.break_start), mStart)).total_seconds())
        for b in breaks if b.break_start
    )
    entry_seconds = max(0, total_seconds - break_seconds)

    remaining = machine.remaining_maintenance_cost or 0
    dep_cost = machine_entry.depreciation_per_second * entry_seconds
    allocated = min(machine_entry.maintenance_rate_per_second * entry_seconds, remaining)

    machine_entry.depreciation_cost = round(dep_cost, 6)
    machine_entry.maintenance_cost = round(allocated, 6)
    machine_entry.allocated_maintenance_cost = round(allocated, 6)
    machine.remaining_maintenance_cost = round(remaining - allocated, 6)


def _compute_and_save_work_run_cost(work_run, breaks):
    """Aggregate material + labor + machine costs and upsert into t_work_run_cost."""
    now = _to_naive(bangkok_now())

    # ── Material cost: cost_per_unit × quantity for each required item ──
    material_cost = 0.0
    for item in (work_run.required_items or []):
        ml = item.material_list
        if ml:
            qty_batch = ml.quantity or 0
            cpu = round(ml.cost_price / qty_batch, 6) if qty_batch > 0 else 0.0
        else:
            cpu = 0.0
        material_cost += cpu * item.quantity

    # ── Labor cost: split into base/day/ot via shift+holiday-aware helper ──
    labor = labor_cost_service.aggregate_labor_costs(
        work_run.assignments or [],
        breaks,
        work_run.created_date,
    )
    base_labor_cost = labor["totals"]["base_cost"]
    day_labor_cost = labor["totals"]["day_cost"]
    ot_labor_cost = labor["totals"]["ot_cost"]
    labor_cost = labor["totals"]["total"]

    # ── Machine cost: sum finalized costs from all machine entries ──
    depreciation_cost = 0.0
    maintenance_cost = 0.0
    for me in (work_run.machines or []):
        depreciation_cost += me.depreciation_cost or 0.0
        maintenance_cost += me.maintenance_cost or 0.0

    total_cost = round(material_cost + depreciation_cost + maintenance_cost + labor_cost, 6)

    existing = db.session.query(WorkRunCost).filter_by(work_run_id=work_run.work_run_id).first()
    if existing:
        existing.material_cost = round(material_cost, 6)
        existing.depreciation_cost = round(depreciation_cost, 6)
        existing.maintenance_cost = round(maintenance_cost, 6)
        existing.base_labor_cost = round(base_labor_cost, 6)
        existing.day_labor_cost = round(day_labor_cost, 6)
        existing.ot_labor_cost = round(ot_labor_cost, 6)
        existing.total_cost = total_cost
    else:
        db.session.add(WorkRunCost(
            work_run_id=work_run.work_run_id,
            material_cost=round(material_cost, 6),
            depreciation_cost=round(depreciation_cost, 6),
            maintenance_cost=round(maintenance_cost, 6),
            base_labor_cost=round(base_labor_cost, 6),
            day_labor_cost=round(day_labor_cost, 6),
            ot_labor_cost=round(ot_labor_cost, 6),
            total_cost=total_cost,
        ))


def get_work_run_by_id(work_run_id):
    work_run = work_run_repository.get_work_run_display(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    return work_run


def get_work_runs_by_work_order(work_order_id):
    return work_run_repository.get_work_runs_by_work_order(work_order_id)


def get_work_runs_cost_by_work_order(work_order_id):
    return work_run_repository.get_work_runs_for_cost_by_work_order(work_order_id)

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
            if src_run.defect_qty is None or qty_equal(src_run.defect_qty, 0):
                raise ValidationError(f"WorkRun {src_run_id} ไม่มีของเสียที่สามารถ rework ได้")

            consumed = work_run_repository.get_consumed_defect_qty_for_work_run(src_run_id)
            outstanding = src_run.defect_qty - consumed
            if src_qty > outstanding + QTY_EPS:
                raise ValidationError(
                    f"WorkRun {src_run_id} มีของเสียคงเหลือ {outstanding} ชิ้น แต่ขอ rework {src_qty} ชิ้น"
                )

            total_rework_qty += src_qty
            validated_sources.append((src_run, src_qty))

        if not qty_equal(total_rework_qty, quantity):
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
        if not qty_equal(qty_from_failed, quantity):
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
    WMS owns actual stock — no qty allocation here. Gate: if the run has
    material requirements, at least one SUCCESS PickingRequest must exist
    on the SalesOrder.
    """
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    if work_run.status != WorkRunStatus.PENDING:
        raise ValidationError(f"Work Run must be PENDING to start (current: {work_run.status.value})")

    work_order = work_order_repository.get_work_order_by_id(work_run.work_order_id)

    required = work_run_repository.get_required_items(work_run_id)
    needs_material = any(req.material_list_id for req in required)
    if needs_material:
        doc_entry = work_order.doc_entry if work_order else None
        if not doc_entry or not picking_request_repository.has_success_picking_request(doc_entry):
            raise ValidationError(
                "ยังไม่มีคำขอเบิกที่สำเร็จ (SUCCESS) สำหรับ Sales Order นี้ — ไม่สามารถเริ่มผลิตได้"
            )

    now = bangkok_now()
    work_run.status = WorkRunStatus.INPROGRESS
    work_run.start_date = now

    if work_order and work_order.status != WorkOrderStatus.INPROGRESS:
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
    if usable_qty < 0 or usable_qty > work_run.quantity + QTY_EPS:
        raise ValidationError(
            f"จำนวนที่ผลิตสำเร็จ ({usable_qty}) ต้องมากกว่า 0 และน้อยกว่าหรือเท่ากับจำนวนที่แพลนไว้ ({work_run.quantity})"
        )

    defect_qty = work_run.quantity - usable_qty
    if defect_qty > QTY_EPS and not data.get("completion_remark", "").strip():
        raise ValidationError("กรุณากรอกหมายเหตุ ในกรณีที่มีสินค้าผลิตผิดพลาด")

    now = bangkok_now()

    # Close open break if any
    active_break = work_run_repository.get_active_break(work_run_id)
    if active_break:
        active_break.break_end = now

    # Close open assignments
    for assignment in work_run_repository.get_open_assignments(work_run_id):
        assignment.to_time = now

    # Close open machines + finalize cost
    breaks = db.session.query(WorkRunBreak).filter(WorkRunBreak.work_run_id == work_run_id).all()
    for machine_entry in work_run_repository.get_open_machines(work_run_id):
        machine_entry.to_time = now
        _allocate_and_finalize_machine_cost(machine_entry, breaks)

    work_run.usable_qty = usable_qty
    work_run.completion_remark = data.get("completion_remark")
    work_run.status = WorkRunStatus.COMPLETED
    work_run.end_date = now

    # Record material actuals (informational only — WMS owns real stock)
    material_actuals = data.get("material_actuals", [])
    for actual in material_actuals:
        req_id = actual.get("work_run_required_item_id")
        if req_id is None:
            continue
        qty_used = actual.get("qty_used") or 0
        if qty_used < 0:
            raise ValidationError(f"qty_used ต้องไม่ติดลบ (required_item {req_id})")

        req = work_run_repository.get_required_item_by_id(req_id)
        if not req or req.work_run_id != work_run_id:
            raise ValidationError(f"required_item {req_id} ไม่ได้อยู่ใน WorkRun นี้")

        req.qty_consumed_actual = qty_used

    # Flush first, then expire all session objects so that identity map cache
    # (populated by get_open_assignments / get_open_machines / get_required_items
    # with lazy='noload' setting relationships to [] / None) does not cause
    # get_work_run_display to return stale empty collections.
    db.session.flush()
    db.session.expire_all()
    full_run = work_run_repository.get_work_run_display(work_run_id)
    fresh_breaks = db.session.query(WorkRunBreak).filter(WorkRunBreak.work_run_id == work_run_id).all()
    _compute_and_save_work_run_cost(full_run, fresh_breaks)

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

    from app.con_sqlalchemy import Employee
    employee_query = db.session.query(Employee).filter(Employee.employee_id == employee_id)
    employee = employee_query.first()
    if not employee:
        raise NotFoundError(f"Employee {employee_id} not found")
    if not employee.is_active:
        raise ValidationError(f"Employee {employee_id} is disabled and cannot be assigned")

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

    from app.con_sqlalchemy import Machine
    machine_query = db.session.query(Machine).filter(Machine.machine_id == machine_id)
    machine = machine_query.first()
    if not machine:
        raise NotFoundError(f"Machine {machine_id} not found")
    if not machine.is_active:
        raise ValidationError(f"Machine {machine_id} is disabled and cannot be assigned")

    existing = work_run_repository.get_open_machine(work_run_id, machine_id)
    if existing:
        raise ValidationError(f"Machine {machine_id} is already assigned to this work run")

    machine_entry = WorkRunMachine(
        work_run_id=work_run_id,
        machine_id=machine_id,
    )
    work_run_repository.save_machine_entry(machine_entry)
    db.session.flush()

    _create_machine_cost_record(machine_entry, machine)

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
    breaks = db.session.query(WorkRunBreak).filter(WorkRunBreak.work_run_id == work_run_id).all()
    _allocate_and_finalize_machine_cost(machine_entry, breaks)
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

    # Per-employee cost — split into base/day/ot via shift+holiday-aware helper
    employee_breakdown = []
    labor = labor_cost_service.aggregate_labor_costs(
        work_run.assignments,
        work_run.breaks,
        work_run.created_date,
    )
    total_base_labor = labor["totals"]["base_cost"]
    total_day_labor = labor["totals"]["day_cost"]
    total_ot_labor = labor["totals"]["ot_cost"]
    total_labor_cost = labor["totals"]["total"]

    for row in labor["rows"]:
        assignment = row["assignment"]
        emp = assignment.employee
        assign_end = assignment.to_time or now
        assign_seconds = max(0, (assign_end - assignment.from_time).total_seconds()) if assignment.from_time else 0
        employee_breakdown.append({
            "employee_id": emp.employee_id if emp else None,
            "employee_first_name": emp.employee_first_name if emp else None,
            "employee_last_name": emp.employee_last_name if emp else None,
            "status": (emp.status.value if hasattr(emp.status, "value") else str(emp.status)) if emp else None,
            "base_salary_at_run": row["base_salary_at_run"],
            "day_rate_at_run": row["day_rate_at_run"],
            "ot_hourly_rate_at_run": row["ot_hourly_rate_at_run"],
            "from_time": assignment.from_time.isoformat() if assignment.from_time else None,
            "to_time": assignment.to_time.isoformat() if assignment.to_time else None,
            "time_spent_seconds": round(assign_seconds, 2),
            "effective_seconds": row["effective_seconds"],
            "base_cost": row["base_cost"],
            "day_cost": row["day_cost"],
            "ot_cost": row["ot_cost"],
            "net_cost": round(row["base_cost"] + row["day_cost"] + row["ot_cost"], 6),
        })

    # Machine time summary + depreciation + maintenance cost
    machine_breakdown = []
    total_depreciation_cost = 0.0
    total_maintenance_cost = 0.0

    for me in work_run.machines:
        m = me.machine
        is_running = me.to_time is None

        dep_per_sec = me.depreciation_per_second or 0.0
        maint_per_sec = me.maintenance_rate_per_second or 0.0

        if is_running:
            dep_cost = me.depreciation_cost  # None until closed
            maint_cost = me.maintenance_cost
            total_cost = None
        else:
            dep_cost = me.depreciation_cost or 0.0
            maint_cost = me.maintenance_cost or 0.0
            total_cost = round((dep_cost or 0.0) + (maint_cost or 0.0), 6)
            total_depreciation_cost += dep_cost or 0.0
            total_maintenance_cost += maint_cost or 0.0

        machine_breakdown.append({
            "work_run_machine_id": me.work_run_machine_id,
            "machine_id": me.machine_id,
            "machine_name": m.machine_name if m else None,
            "machine_code": m.machine_code if m else None,
            "is_second_hand": m.is_second_hand if m else False,
            "from_time": me.from_time.isoformat() if me.from_time else None,
            "to_time": me.to_time.isoformat() if me.to_time else None,
            "cost": {
                "depreciation_per_second": dep_per_sec,
                "depreciation_cost": dep_cost,
                "maintenance_rate_per_second": maint_per_sec,
                "maintenance_cost": maint_cost,
                "total_cost": total_cost,
            },
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
        "total_base_labor_cost": round(total_base_labor, 6),
        "total_day_labor_cost": round(total_day_labor, 6),
        "total_ot_labor_cost": round(total_ot_labor, 6),
        "total_labor_cost": round(total_labor_cost, 6),
        "total_depreciation_cost": round(total_depreciation_cost, 6),
        "total_maintenance_cost": round(total_maintenance_cost, 6),
        "total_machine_cost": round(total_depreciation_cost + total_maintenance_cost, 6),
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


def delete_required_item(required_item_id):
    req = work_run_repository.get_required_item_by_id(required_item_id)
    if not req:
        raise NotFoundError(f"Required item {required_item_id} not found")
    db.session.delete(req)
    db.session.commit()


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
