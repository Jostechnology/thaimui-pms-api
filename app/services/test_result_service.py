from app.con_sqlalchemy import (
    TestResult, TestResultItem, TestResultStatus, TestSessionStatus,
    TestResultWorkRun, TestResultPickingItem, TestResultRequiredItem,
    TestResultAssignment, TestResultMachine, TestResultCost, TestResultBreak,
    Machine, MaterialList, BreakType,
    WorkRunStatus, WorkRunTransactionType, QCWorkOrder, QCWorkOrderStatus,
    AllocationMode, bangkok_now,
)
from app.ma_sqlalchemy import TestResultSchema
from app.repositories import (
    test_result_repository, qc_work_order_repository,
    work_run_repository, picking_request_repository,
)
from app.services import transaction_service, document_code_service, picking_allocation_service
from app.app import db
from app.exception import NotFoundError, ValidationError
from sqlalchemy.orm import joinedload


def _naive(dt):
    """Strip timezone info so datetime arithmetic works against DB-loaded naive datetimes."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _resolve_status(val):
    if not val:
        return TestResultStatus.PASSED
    if isinstance(val, TestResultStatus):
        return val
    try:
        return TestResultStatus[val.strip().upper()]
    except KeyError:
        return TestResultStatus.PASSED


def _validate_work_run_sources(qc, sales_item, claimed_qty, data):
    """Validate work_run_sources for produced items. Returns [(work_run_id, qty)]."""
    work_run_sources_data = data.get("work_run_sources", [])
    if not work_run_sources_data:
        raise ValidationError("ต้องระบุ work_run_sources อย่างน้อย 1 รายการ")

    total_from_runs = 0
    validated_sources = []
    work_order_id = sales_item.work_order.work_order_id if sales_item.work_order else None

    for src in work_run_sources_data:
        wr_id = src.get("work_run_id")
        qty = src.get("qty_from_run")

        if not wr_id:
            raise ValidationError("work_run_id ไม่ถูกต้อง")
        if not qty or qty <= 0:
            raise ValidationError(f"qty_from_run ของ work_run {wr_id} ต้องมากกว่า 0")

        work_run = work_run_repository.get_work_run_by_id(wr_id)
        if not work_run:
            raise NotFoundError(f"ไม่พบ WorkRun ID {wr_id}")
        if work_run.status != WorkRunStatus.COMPLETED:
            raise ValidationError(f"WorkRun {wr_id} ยังไม่เสร็จสิ้น (ต้องเป็น COMPLETED)")
        if work_order_id and work_run.work_order_id != work_order_id:
            raise ValidationError(f"WorkRun {wr_id} ไม่ได้อยู่ใน WorkOrder ของสินค้านี้")

        committed = test_result_repository.get_committed_qty_for_work_run(wr_id)
        remaining = (work_run.usable_qty or 0) - committed
        if qty > remaining:
            raise ValidationError(
                f"WorkRun {wr_id} มีจำนวนที่เทสได้เหลือ {remaining} แต่ขอ {qty}"
            )

        total_from_runs += qty
        validated_sources.append((wr_id, qty))

    if total_from_runs != claimed_qty:
        raise ValidationError(
            f"ผลรวม qty_from_run ({total_from_runs}) ต้องเท่ากับ claimed_qty ({claimed_qty})"
        )

    return validated_sources


def _apply_actuals_reverse_fifo(allocation_rows, qty_used_actual):
    """
    Distribute qty_used_actual across FIFO-ordered allocation rows.
    Releases leftover from the LAST rows first (reverse FIFO).
    Sets qty_consumed on each row.
    """
    total_allocated = sum(r.qty_allocated for r in allocation_rows)

    if qty_used_actual > total_allocated:
        # Operator used more than allocated (over-consumption) — cap at allocated
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


def create_test_result(qc_work_order_id, data):
    """
    Phase 1 — create TestResult in PENDING.
    Validates claimed_qty against available. For produced items, validates work_run_sources.
    Seeds TestResultRequiredItem from QCItem rows that have material_list_id.
    No PR pool deduction at this stage.
    """
    try:
        qc = qc_work_order_repository.get_qc_work_order_for_availability_check(qc_work_order_id)
        sales_item = qc.sales_item

        claimed_qty = data.get("claimed_qty")
        if not claimed_qty or claimed_qty <= 0:
            raise ValidationError("จำนวนที่ขอเทสต้องมากกว่า 0")

        available = sales_item.available_for_test_qty
        if claimed_qty > available:
            raise ValidationError(
                f"จำนวนที่ขอเทส ({claimed_qty}) มีมากกว่าจำนวนสินค้าที่สามารถเทสได้ ({available})"
            )

        test_result = TestResult(
            qc_work_order_id=qc_work_order_id,
            test_result_code=document_code_service.generate_number("TR"),
            claimed_qty=claimed_qty,
            session_status=TestSessionStatus.PENDING,
            remark=data.get("remark"),
        )
        test_result_repository.create_test_result(test_result)
        db.session.flush()

        if qc.status == QCWorkOrderStatus.PENDING:
            qc.status = QCWorkOrderStatus.INPROGRESS

        # For produced items: validate + record work_run_sources immediately
        if sales_item.produce:
            validated_sources = _validate_work_run_sources(qc, sales_item, claimed_qty, data)
            for wr_id, qty in validated_sources:
                db.session.add(TestResultWorkRun(
                    test_result_id=test_result.test_result_id,
                    work_run_id=wr_id,
                    qty_from_run=qty,
                ))

        # Required items are NOT auto-seeded — operator adds them manually via
        # POST /api/test_result/<id>/required_items while status is PENDING.
        # QCItem rows serve as reference/instruction only.

        db.session.commit()
        db.session.refresh(test_result)
        return test_result_repository.get_test_result_by_id(test_result.test_result_id)
    except Exception:
        db.session.rollback()
        raise


def start_test_result(test_result_id, data=None):
    """
    Phase 2 — PENDING → INPROGRESS.
    Allocates picking items either by FIFO (auto) or operator-chosen (manual).

    data (optional):
        allocation_mode: "auto" (default) or "manual"
        sales_item_sources: [{picking_request_item_id, qty}]       — manual only, for non-produced sales item
        material_sources:   [{required_item_id, sources: [{picking_request_item_id, qty}]}]  — manual only
    """
    if data is None:
        data = {}

    allocation_mode_str = data.get("allocation_mode", "auto").upper()
    if allocation_mode_str not in ("AUTO", "MANUAL"):
        raise ValidationError(f"allocation_mode ไม่ถูกต้อง: {allocation_mode_str}")
    is_manual = allocation_mode_str == "MANUAL"
    mode_enum = AllocationMode.MANUAL if is_manual else AllocationMode.AUTO

    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        if test_result.session_status != TestSessionStatus.PENDING:
            raise ValidationError(
                f"TestResult must be PENDING to start (current: {test_result.session_status.value})"
            )

        qc = qc_work_order_repository.get_qc_work_order_for_availability_check(
            test_result.qc_work_order_id
        )
        sales_item = qc.sales_item

        shortages = []
        sales_item_allocations = []   # [(pri_id, qty)]
        material_allocations = []     # [(req_item, [(pri_id, qty)])]

        # Allocate claimed_qty for non-produced items from PR pool
        if not sales_item.produce:
            if is_manual:
                manual_si_sources = data.get("sales_item_sources", [])
                if not manual_si_sources:
                    raise ValidationError("manual mode ต้องระบุ sales_item_sources สำหรับ non-produced item")
                try:
                    sales_item_allocations = picking_allocation_service.allocate_manual(
                        manual_si_sources, test_result.claimed_qty
                    )
                except ValidationError:
                    raise
            else:
                candidates = picking_request_repository.get_available_picking_items_for_sales_item(
                    sales_item.sales_item_id
                )
                try:
                    sales_item_allocations = picking_allocation_service.allocate_fifo(
                        candidates, test_result.claimed_qty
                    )
                except ValidationError:
                    shortages.append(
                        f"{sales_item.item_code} ({sales_item.item_name}) "
                        f"ต้องการ {test_result.claimed_qty} ชิ้น"
                    )

        # Allocate each required material from PR pool
        required = test_result_repository.get_required_items(test_result_id)

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
                try:
                    allocs = picking_allocation_service.allocate_manual(sources, req.required_qty)
                    material_allocations.append((req, allocs))
                except ValidationError:
                    raise
            else:
                candidates = picking_request_repository.get_available_picking_items_for_material(
                    req.material_list_id
                )
                try:
                    allocs = picking_allocation_service.allocate_fifo(candidates, req.required_qty)
                    material_allocations.append((req, allocs))
                except ValidationError:
                    shortages.append(f"{req.item_code} ({req.item_name})")

        if shortages:
            raise ValidationError(
                f"วัตถุดิบในคลังไม่พอ: {', '.join(shortages)}"
            )

        # Commit sales-item allocations
        for pri_id, qty in sales_item_allocations:
            db.session.add(TestResultPickingItem(
                test_result_id=test_result_id,
                picking_request_item_id=pri_id,
                test_result_required_item_id=None,
                qty_allocated=qty,
                allocation_mode=mode_enum,
            ))

        # Commit material allocations (linked to required item for reverse-FIFO release)
        for req, allocs in material_allocations:
            for pri_id, qty in allocs:
                db.session.add(TestResultPickingItem(
                    test_result_id=test_result_id,
                    picking_request_item_id=pri_id,
                    test_result_required_item_id=req.id,
                    qty_allocated=qty,
                    allocation_mode=mode_enum,
                ))

        # For produced items: fire SENT_TO_TESTING transaction now (was at create before)
        if sales_item.produce:
            for trw in test_result.work_run_sources:
                source_run = work_run_repository.get_work_run_by_id(trw.work_run_id)
                transaction_service.create_work_run_transaction(
                    source_run,
                    WorkRunTransactionType.SENT_TO_TESTING,
                    trw.qty_from_run,
                    f"TEST-{test_result_id}",
                )

        test_result.session_status = TestSessionStatus.INPROGRESS
        test_result.started_at = _naive(bangkok_now())
        db.session.commit()
        return test_result_repository.get_test_result_by_id(test_result_id)
    except Exception:
        db.session.rollback()
        raise


def finalize_test_result(test_result_id, data):
    """
    Phase 3 — INPROGRESS → COMPLETED.
    Accepts per-item test results and optional material_actuals for leftover release.

    material_actuals: [{test_result_required_item_id, qty_used}]
    Omitted rows default to full allocation (no leftover released).
    """
    try:
        test_result = test_result_repository.get_test_result_for_finalize(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        if test_result.session_status == TestSessionStatus.COMPLETED:
            raise ValidationError("เทสนี้จบไปแล้ว กรุณาตรวจสอบอีกครั้ง")
        if test_result.session_status == TestSessionStatus.PENDING:
            raise ValidationError("ต้องกด Start ก่อน finalize")

        items_data = data.get("items", [])
        if not items_data:
            raise ValidationError("ไม่พบ TestItem กรุณาตรวจสอบอีกครั้ง")

        test_result.test_method = data.get("test_method")
        test_result.standard_reference = data.get("standard_reference")
        test_result.remark = data.get("remark", test_result.remark)

        for it in items_data:
            item = TestResultItem(
                unit_number=it.get("unit_number"),
                serial_no=it.get("serial_no"),
                wll_measured=float(it.get("wll_measured")) if it.get("wll_measured") is not None else None,
                load_test_value=float(it.get("load_test_value")) if it.get("load_test_value") is not None else None,
                description=it.get("description"),
                result=_resolve_status(it.get("result")),
                remark=it.get("remark"),
            )
            test_result.test_result_items.append(item)

        overall = _resolve_status(data.get("overall_status"))
        test_result.overall_status = overall
        test_result.session_status = TestSessionStatus.COMPLETED

        if overall == TestResultStatus.PASSED and test_result.qc_work_order:
            test_result.qc_work_order.status = QCWorkOrderStatus.PASSED

        # Apply material actuals — release leftover back to pool via reverse-FIFO
        material_actuals = data.get("material_actuals", [])
        reported_req_ids = set()
        for actual in material_actuals:
            req_id = actual.get("test_result_required_item_id")
            if req_id is None:
                continue
            qty_used = actual.get("qty_used") or 0
            if qty_used < 0:
                raise ValidationError(f"qty_used ต้องไม่ติดลบ (required_item {req_id})")

            req = test_result_repository.get_required_item_by_id(req_id)
            if not req or req.test_result_id != test_result_id:
                raise ValidationError(f"required_item {req_id} ไม่ได้อยู่ใน TestResult นี้")

            req.qty_consumed_actual = qty_used
            allocation_rows = test_result_repository.get_trpi_rows_for_required_item(req_id)
            _apply_actuals_reverse_fifo(allocation_rows, qty_used)
            reported_req_ids.add(req_id)

        # Rows not reported → default full consumption (qty_consumed = qty_allocated)
        required = test_result_repository.get_required_items(test_result_id)
        for req in required:
            if req.id not in reported_req_ids:
                allocation_rows = test_result_repository.get_trpi_rows_for_required_item(req.id)
                for r in allocation_rows:
                    r.qty_consumed = r.qty_allocated

        # Auto-close any open assignments
        now_naive = _naive(bangkok_now())
        open_assignments = (
            db.session.query(TestResultAssignment)
            .filter(TestResultAssignment.test_result_id == test_result_id,
                    TestResultAssignment.to_time == None)
            .all()
        )
        for a in open_assignments:
            a.to_time = now_naive

        # Close any open break (session ended while paused)
        active_break = test_result_repository.get_active_break(test_result_id)
        if active_break:
            active_break.break_end = now_naive

        db.session.flush()

        # Load all breaks for cost deduction
        all_breaks = test_result_repository.get_all_breaks(test_result_id)

        # Auto-close any open machine entries and calculate their costs (deducting break time)
        open_machines = (
            db.session.query(TestResultMachine)
            .filter(TestResultMachine.test_result_id == test_result_id,
                    TestResultMachine.to_time == None)
            .all()
        )
        for m in open_machines:
            m.to_time = now_naive
            machine = db.session.query(Machine).filter(Machine.machine_id == m.machine_id).first()
            if machine:
                m_start = _naive(m.from_time)
                m_end = now_naive
                total_secs = max(0, (m_end - m_start).total_seconds())
                break_secs = sum(
                    max(0, (min(_naive(b.break_end or m_end), m_end)
                            - max(_naive(b.break_start), m_start)).total_seconds())
                    for b in all_breaks if b.break_start
                )
                eff_secs = max(0, total_secs - break_secs)
                remaining = machine.remaining_maintenance_cost or 0
                dep = m.depreciation_per_second * eff_secs
                allocated = min(m.maintenance_rate_per_second * eff_secs, remaining)
                m.depreciation_cost = round(dep, 6)
                m.maintenance_cost = round(allocated, 6)
                m.allocated_maintenance_cost = round(allocated, 6)
                machine.remaining_maintenance_cost = round(remaining - allocated, 6)

        db.session.flush()

        # Calculate total costs and create TestResultCost record
        # populate_existing=True forces SQLAlchemy to re-populate the employee
        # relationship even for objects already in the identity map (loaded without
        # joinedload in the open_assignments query above, leaving employee=None).
        all_assignments = (
            db.session.query(TestResultAssignment)
            .options(joinedload(TestResultAssignment.employee))
            .filter(TestResultAssignment.test_result_id == test_result_id)
            .populate_existing()
            .all()
        )
        labor_cost = 0.0
        for a in all_assignments:
            if a.employee and a.from_time and a.to_time:
                a_start = _naive(a.from_time)
                a_end = _naive(a.to_time)
                total_secs = max(0, (a_end - a_start).total_seconds())
                break_secs = sum(
                    max(0, (min(_naive(b.break_end or a_end), a_end)
                            - max(_naive(b.break_start), a_start)).total_seconds())
                    for b in all_breaks if b.break_start
                )
                eff_secs = max(0, total_secs - break_secs)
                rate = (a.employee.salary_base or 0) / 30 / 8 / 3600
                labor_cost += rate * eff_secs

        all_machines = (
            db.session.query(TestResultMachine)
            .filter(TestResultMachine.test_result_id == test_result_id)
            .all()
        )
        dep_cost_total = sum(m.depreciation_cost or 0 for m in all_machines)
        maint_cost_total = sum(m.maintenance_cost or 0 for m in all_machines)

        # required items อยู่ใน identity map แล้ว (จาก get_required_items ข้างบน) พร้อม
        # material_list = None (committed-by-noload) ทำให้ joinedload ไม่ override ได้
        # → query MaterialList ตรงๆ ด้วย FK แทน
        ml_ids = [ri.material_list_id for ri in required if ri.material_list_id]
        ml_map: dict = {}
        if ml_ids:
            ml_rows = (
                db.session.query(MaterialList)
                .filter(MaterialList.material_list_id.in_(ml_ids))
                .all()
            )
            ml_map = {ml.material_list_id: ml for ml in ml_rows}

        mat_cost = 0.0
        for ri in required:
            if ri.material_list_id:
                ml = ml_map.get(ri.material_list_id)
                if ml:
                    qty = ri.qty_consumed_actual if ri.qty_consumed_actual is not None else (ri.required_qty or 0)
                    mat_cost += ml.cost_per_unit * qty

        cost_record = TestResultCost(
            test_result_id=test_result_id,
            labor_cost=round(labor_cost, 4),
            depreciation_cost=round(dep_cost_total, 4),
            maintenance_cost=round(maint_cost_total, 4),
            material_cost=round(mat_cost, 4),
            total_cost=round(labor_cost + dep_cost_total + maint_cost_total + mat_cost, 4),
        )
        db.session.add(cost_record)

        db.session.commit()
        db.session.refresh(test_result)
        return test_result_repository.get_test_result_by_id(test_result_id)
    except Exception:
        db.session.rollback()
        raise

def get_test_results_by_qc_work_order(qc_work_order_id):
    try:
        results = test_result_repository.get_test_results_by_qc_work_order(qc_work_order_id)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def get_test_results_cost_by_qc_work_order(qc_work_order_id):
    try:
        results = test_result_repository.get_test_results_cost_by_qc_work_order(qc_work_order_id)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def get_test_result_by_id(test_result_id):
    try:
        result = test_result_repository.get_test_result_by_id(test_result_id)
        if not result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        return TestResultSchema().dump(result)
    except Exception:
        raise


def update_test_result(test_result_id, data):
    """Update metadata on a non-COMPLETED session."""
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        if test_result.session_status == TestSessionStatus.COMPLETED:
            raise ValidationError("Cannot edit a finalized test session")

        if "remark" in data:
            test_result.remark = data["remark"]

        db.session.commit()
        return TestResultSchema().dump(test_result)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def get_test_results_by_sales_item(sales_item_id):
    try:
        results = test_result_repository.get_test_results_by_sales_item(sales_item_id)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def get_test_results_by_doc_entry(doc_entry):
    try:
        results = test_result_repository.get_test_results_by_doc_entry(doc_entry)
        return TestResultSchema(many=True).dump(results)
    except Exception:
        raise


def add_required_item(test_result_id, items):
    """Replace material requirements for a PENDING TestResult (delete-then-insert)."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
    if test_result.session_status != TestSessionStatus.PENDING:
        raise ValidationError("เพิ่มรายการได้เฉพาะตอน PENDING")

    db.session.query(TestResultRequiredItem).filter(
        TestResultRequiredItem.test_result_id == test_result_id
    ).delete(synchronize_session=False)

    for i, data in enumerate(items):
        item_code = (data.get("item_code") or "").strip()
        item_name = (data.get("item_name") or "").strip()
        required_qty = data.get("required_qty")

        if not item_code:
            raise ValidationError(f"item[{i}]: item_code ต้องระบุ")
        if not item_name:
            raise ValidationError(f"item[{i}]: item_name ต้องระบุ")
        if not required_qty or required_qty <= 0:
            raise ValidationError(f"item[{i}]: required_qty ต้องมากกว่า 0")

        req = TestResultRequiredItem(
            test_result_id=test_result_id,
            qc_item_id=data.get("qc_item_id"),
            material_list_id=data.get("material_list_id"),
            item_code=item_code,
            item_name=item_name,
            required_qty=required_qty,
            unit=data.get("unit"),
        )
        db.session.add(req)

    db.session.commit()
    return test_result_repository.get_required_items(test_result_id)


def get_required_items_for_test_result(test_result_id):
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
    return test_result_repository.get_required_items(test_result_id)


def delete_required_item(test_result_id, required_item_id):
    """Remove a required item from a PENDING TestResult."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
    if test_result.session_status != TestSessionStatus.PENDING:
        raise ValidationError("ลบรายการได้เฉพาะตอน PENDING")

    req = test_result_repository.get_required_item_by_id(required_item_id)
    if not req or req.test_result_id != test_result_id:
        raise NotFoundError(f"ไม่พบรายการ required_item {required_item_id}")

    db.session.delete(req)
    db.session.commit()
    return test_result_repository.get_required_items(test_result_id)


def get_pick_requests_for_test_result(test_result_id):
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError("ไม่พบ Test Result ที่ระบุ")

    qc = qc_work_order_repository.get_qc_work_order_for_availability_check(test_result.qc_work_order_id)
    sales_item = qc.sales_item

    sales_item_id = None if sales_item.produce else sales_item.sales_item_id
    required = test_result_repository.get_required_items(test_result_id)
    material_list_ids = [r.material_list_id for r in required if r.material_list_id]

    return picking_request_repository.get_available_pick_requests_for_test_result(
        sales_item_id=sales_item_id,
        material_list_ids=material_list_ids or None,
    )


def assign_employee(test_result_id, employee_id):
    """Open a new assignment for an employee on this test result."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")
    if test_result.session_status not in (TestSessionStatus.INPROGRESS, TestSessionStatus.PAUSED):
        raise ValidationError("Can only assign employees to an active (INPROGRESS or PAUSED) test session")

    existing = test_result_repository.get_open_assignment(test_result_id, employee_id)
    if existing:
        raise ValidationError(f"Employee {employee_id} already has an open assignment on this test session")

    assignment = TestResultAssignment(
        test_result_id=test_result_id,
        employee_id=employee_id,
    )
    test_result_repository.save_assignment(assignment)
    db.session.commit()
    return test_result_repository.get_test_result_by_id(test_result_id)


def unassign_employee(test_result_id, employee_id):
    """Close the open assignment for an employee."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")

    assignment = test_result_repository.get_open_assignment(test_result_id, employee_id)
    if not assignment:
        raise NotFoundError(f"Employee {employee_id} has no open assignment on Test Result {test_result_id}")

    assignment.to_time = bangkok_now()
    db.session.commit()
    return test_result_repository.get_test_result_by_id(test_result_id)


def _calc_tr_depreciation_per_second(machine):
    pp = machine.purchase_price or 0
    uly = machine.useful_life_years or 0
    whpd = machine.working_hours_per_day or 0
    if pp > 0 and uly > 0 and whpd > 0:
        total_sec = uly * 365 * whpd * 3600
        if total_sec > 0:
            return pp / total_sec
    return 0.0


def _calc_tr_maintenance_rate_per_second(machine):
    remaining = machine.remaining_maintenance_cost or 0
    if remaining <= 0:
        return 0.0
    from app.con_sqlalchemy import TestResultMachine as TRM
    past_seconds = db.session.query(
        db.func.coalesce(
            db.func.sum(
                db.func.greatest(0, db.func.timestampdiff(
                    db.text('SECOND'), TRM.from_time, TRM.to_time
                ))
            ), 0
        )
    ).filter(TRM.machine_id == machine.machine_id, TRM.to_time != None).scalar() or 0

    accumulated_sec = (machine.accumulated_hours or 0) * 3600 if machine.is_second_hand else 0
    total_past_sec = float(past_seconds) + accumulated_sec
    if total_past_sec > 0:
        return remaining / total_past_sec
    return 0.0


def assign_machine(test_result_id, machine_id):
    """Open a new machine entry for this test result."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")
    if test_result.session_status not in (TestSessionStatus.INPROGRESS, TestSessionStatus.PAUSED):
        raise ValidationError("Can only assign machines to an active (INPROGRESS or PAUSED) test session")

    existing = test_result_repository.get_open_machine(test_result_id, machine_id)
    if existing:
        raise ValidationError(f"Machine {machine_id} is already assigned to this test session")

    machine_entry = TestResultMachine(
        test_result_id=test_result_id,
        machine_id=machine_id,
    )
    test_result_repository.save_machine_entry(machine_entry)
    db.session.flush()

    machine = db.session.query(Machine).filter(Machine.machine_id == machine_id).first()
    if machine:
        machine_entry.depreciation_per_second = _calc_tr_depreciation_per_second(machine)
        machine_entry.maintenance_rate_per_second = _calc_tr_maintenance_rate_per_second(machine)

    db.session.commit()
    return test_result_repository.get_test_result_by_id(test_result_id)


def unassign_machine(test_result_id, machine_id):
    """Close the open machine entry and finalize its cost."""
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError(f"Test Result {test_result_id} not found")

        machine_entry = test_result_repository.get_open_machine(test_result_id, machine_id)
        if not machine_entry:
            raise NotFoundError(f"Machine {machine_id} has no open entry on Test Result {test_result_id}")

        now_naive = _naive(bangkok_now())
        machine_entry.to_time = now_naive

        machine = db.session.query(Machine).filter(Machine.machine_id == machine_id).first()
        if machine:
            entry_seconds = max(0, (now_naive - _naive(machine_entry.from_time)).total_seconds())
            remaining = machine.remaining_maintenance_cost or 0
            dep_cost = machine_entry.depreciation_per_second * entry_seconds
            allocated = min(machine_entry.maintenance_rate_per_second * entry_seconds, remaining)
            machine_entry.depreciation_cost = round(dep_cost, 6)
            machine_entry.maintenance_cost = round(allocated, 6)
            machine_entry.allocated_maintenance_cost = round(allocated, 6)
            machine.remaining_maintenance_cost = round(remaining - allocated, 6)

        db.session.commit()
        return test_result_repository.get_test_result_by_id(test_result_id)
    except Exception:
        db.session.rollback()
        raise


def pause_test_result(test_result_id, data):
    """INPROGRESS → PAUSED. Creates a TestResultBreak with break_start=now."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")
    if test_result.session_status != TestSessionStatus.INPROGRESS:
        raise ValidationError(f"Test Result must be INPROGRESS to pause (current: {test_result.session_status.value})")

    break_type_str = data.get("break_type", "OTHER")
    try:
        break_type = BreakType(break_type_str)
    except ValueError:
        raise ValidationError(f"Invalid break_type: {break_type_str}")

    test_result.session_status = TestSessionStatus.PAUSED
    tr_break = TestResultBreak(
        test_result_id=test_result_id,
        break_type=break_type,
        remark=data.get("remark"),
    )
    test_result_repository.save_break(tr_break)
    db.session.commit()
    return test_result_repository.get_test_result_by_id(test_result_id)


def resume_test_result(test_result_id):
    """PAUSED → INPROGRESS. Closes the active break."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")
    if test_result.session_status != TestSessionStatus.PAUSED:
        raise ValidationError(f"Test Result must be PAUSED to resume (current: {test_result.session_status.value})")

    active_break = test_result_repository.get_active_break(test_result_id)
    if active_break:
        active_break.break_end = bangkok_now()

    test_result.session_status = TestSessionStatus.INPROGRESS
    db.session.commit()
    return test_result_repository.get_test_result_by_id(test_result_id)


def delete_test_result(test_result_id):
    """PENDING and INPROGRESS sessions can be deleted. COMPLETED cannot."""
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        if test_result.session_status == TestSessionStatus.COMPLETED:
            raise ValidationError("Cannot delete a finalized test session")
        test_result_repository.delete_test_result(test_result_id)
        db.session.commit()
        return {"message": f"ลบ Test Result ID {test_result_id} สำเร็จ"}
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))
