from app.con_sqlalchemy import TestResult, TestResultItem, TestResultStatus, TestSessionStatus, TestResultWorkRun, WorkRunStatus, WorkRunTransactionType
from app.ma_sqlalchemy import TestResultSchema
from app.repositories import test_result_repository, qc_work_order_repository, work_run_repository
from app.services import transaction_service
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


def create_test_result(qc_work_order_id, data):
    """
    Phase 1 — claim items for a test session.
    Validates:
      - claimed_qty <= sales_item.available_for_test_qty
      - each work_run is COMPLETED and belongs to this sales_item's work_order
      - sum of qty_from_run == claimed_qty
      - qty_from_run for each run <= that run's remaining testable qty
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

        test_result = TestResult(
            qc_work_order_id=qc_work_order_id,
            claimed_qty=claimed_qty,
            session_status=TestSessionStatus.INPROGRESS,
            remark=data.get("remark"),
        )
        test_result_repository.create_test_result(test_result)
        db.session.flush()

        for wr_id, qty in validated_sources:
            db.session.add(TestResultWorkRun(
                test_result_id=test_result.test_result_id,
                work_run_id=wr_id,
                qty_from_run=qty,
            ))
            source_run = work_run_repository.get_work_run_by_id(wr_id)
            transaction_service.create_work_run_transaction(
                source_run,
                WorkRunTransactionType.SENT_TO_TESTING,
                qty,
                f"TEST-{test_result.test_result_id}",
            )

        db.session.commit()
        db.session.refresh(test_result)
        return TestResultSchema().dump(test_result)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


def finalize_test_result(test_result_id, data):
    """
    Phase 2 — submit test results and close the session.
    Fires TESTED_PASSED / TESTED_FAILED transactions based on per-item results.
    """
    try:
        test_result = test_result_repository.get_test_result_for_finalize(test_result_id)
        if not test_result:
            raise NotFoundError("ไม่พบ Test Result ที่ระบุ")
        if test_result.session_status == TestSessionStatus.COMPLETED:
            raise ValidationError("เทสนี้จบไปแล้ว กรุณาตรวจสอบอีกครั้ง")

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

        db.session.commit()
        db.session.refresh(test_result)
        return TestResultSchema().dump(test_result)
    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))


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
    """Update metadata on an INPROGRESS session only. Cannot edit a finalized session."""
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


def delete_test_result(test_result_id):
    """Only INPROGRESS sessions can be deleted."""
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
