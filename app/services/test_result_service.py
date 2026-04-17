from app.con_sqlalchemy import (
    TestResult, TestResultItem, TestResultStatus, TestSessionStatus,
    TestResultWorkRun, TestResultPickingItem, TestResultRequiredItem,
    WorkRunStatus, WorkRunTransactionType, QCWorkOrder, QCWorkOrderStatus,
)
from app.ma_sqlalchemy import TestResultSchema
from app.repositories import (
    test_result_repository, qc_work_order_repository,
    work_run_repository, picking_request_repository,
)
from app.services import transaction_service, document_code_service, picking_allocation_service
from app.app import db
from app.exception import NotFoundError, ValidationError


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


def start_test_result(test_result_id):
    """
    Phase 2 — PENDING → INPROGRESS.
    FIFO-allocates:
      - claimed_qty from PR pool for non-produced sales items
      - each required material from PR pool
    Raises ValidationError (with shortage list) if pool insufficient.
    """
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
        for req in required:
            if not req.material_list_id:
                continue
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
            ))

        # Commit material allocations (linked to required item for reverse-FIFO release)
        for req, allocs in material_allocations:
            for pri_id, qty in allocs:
                db.session.add(TestResultPickingItem(
                    test_result_id=test_result_id,
                    picking_request_item_id=pri_id,
                    test_result_required_item_id=req.id,
                    qty_allocated=qty,
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

        test_result.test_date = data.get("test_date")
        test_result.tested_by = data.get("tested_by")
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
            qty_used = actual.get("qty_used")
            if req_id is None or qty_used is None:
                continue
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
    """Add material requirements to a PENDING TestResult. Accepts a list."""
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
    if test_result.session_status != TestSessionStatus.PENDING:
        raise ValidationError("เพิ่มรายการได้เฉพาะตอน PENDING")

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
