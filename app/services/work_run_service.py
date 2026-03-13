from app.con_sqlalchemy import WorkRun, WorkRunStatus, SalesItemTransactionType
from app.repositories import work_run_repository, work_order_repository
from app.app import db
from app.exception import NotFoundError, ValidationError
from app.services import transaction_service


def get_work_run_by_id(work_run_id):
    try:
        work_run = work_run_repository.get_work_run_with_test_results(work_run_id)
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


def create_work_run(work_order_id, data):
    """Create a new WorkRun (rework) on an existing WorkOrder. No transaction yet — fires on completion."""
    try:
        work_order = work_order_repository.get_work_order_by_id(work_order_id)
        if not work_order:
            raise NotFoundError(f"Work Order {work_order_id} not found")

        quantity = data.get("quantity", 1)
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
        work_run = work_run_repository.get_work_run_with_sales_item(work_run_id)
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

        if usable_qty > 0:
            transaction_service.create_sales_item_transaction(
                work_run.work_order.sales_item,
                str(work_run.work_run_id),
                SalesItemTransactionType.PRODUCED,
                usable_qty,
            )

        db.session.commit()
        return work_run
    except Exception:
        db.session.rollback()
        raise
