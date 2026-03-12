from app.con_sqlalchemy import WorkRun, WorkRunStatus, SalesItemTransactionType
from app.repositories import work_run_repository, work_order_repository
from app.app import db
from app.exception import NotFoundError, ValidationError
from app.services import transaction_service


def get_work_run_by_id(work_run_id):
    try:
        work_run = work_run_repository.get_work_run_with_test_result(work_run_id)
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
    """Create a new WorkRun (rework) on an existing WorkOrder."""
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
        db.session.flush()

        transaction_service.create_sales_item_transaction(
            work_order.sales_item, work_run, SalesItemTransactionType.PRODUCED, quantity
        )

        db.session.commit()
        return work_run
    except Exception:
        db.session.rollback()
        raise


def complete_work_run(work_run_id):
    try:
        work_run = work_run_repository.get_work_run_by_id(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")
        if work_run.status == WorkRunStatus.COMPLETED:
            raise ValidationError("Work Run is already completed")
        work_run.status = WorkRunStatus.COMPLETED
        db.session.commit()
        return work_run
    except Exception:
        db.session.rollback()
        raise
