from app.con_sqlalchemy import WorkRun, WorkRunStatus, WorkRunReworkSource, TestSessionStatus, TestResultStatus
from app.repositories import work_run_repository, work_order_repository, test_result_repository
from app.services import transaction_service
from app.con_sqlalchemy import WorkRunTransactionType
from app.app import db
from app.exception import NotFoundError, ValidationError


def get_work_run_by_id(work_run_id):
    try:
        work_run = work_run_repository.get_work_run_display(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")
        return work_run
    except Exception:
        raise


def get_work_runs_by_work_order(work_order_id):
    try:
        return work_run_repository.get_work_runs_by_work_order(work_order_id)
    except Exception:
        raise


def get_work_runs_by_sales_item(sales_item_id):
    try:
        return work_run_repository.get_work_runs_by_sales_item(sales_item_id)
    except Exception:
        raise


def create_work_run(work_order_id, data):
    """
    Create a new WorkRun on an existing WorkOrder.

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
    try:
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
                wms_pick_reference=data.get("wms_pick_reference"),
                status=WorkRunStatus.INPROGRESS,
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
                wms_pick_reference=data.get("wms_pick_reference"),
                status=WorkRunStatus.INPROGRESS,
                rework_source_test_result_id=rework_source_test_result_id,
                qty_from_failed=qty_from_failed,
            )
            work_run_repository.create_work_run(work_run)

        # --- No rework source: regular new run ---
        else:
            work_run = WorkRun(
                work_order_id=work_order_id,
                quantity=quantity,
                wms_pick_reference=data.get("wms_pick_reference"),
                status=WorkRunStatus.INPROGRESS,
            )
            work_run_repository.create_work_run(work_run)

        db.session.commit()
        return work_run
    except Exception:
        db.session.rollback()
        raise


def complete_work_run(work_run_id, data):
    """
    Complete a WorkRun and record actual usable output.

    Required in data:
    - usable_qty (int): how many items actually came out good
    - completion_remark (str): required when usable_qty < quantity (explains the defects)
    """
    try:
        work_run = work_run_repository.get_work_run_by_id(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")
        if work_run.status == WorkRunStatus.COMPLETED:
            raise ValidationError("Work Run is already completed")

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

        work_run.usable_qty = usable_qty
        work_run.completion_remark = data.get("completion_remark")
        work_run.status = WorkRunStatus.COMPLETED

        db.session.commit()
        return work_run
    except Exception:
        db.session.rollback()
        raise
