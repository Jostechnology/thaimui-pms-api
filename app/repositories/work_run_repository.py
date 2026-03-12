from app.con_sqlalchemy import WorkRun, WorkOrder, SalesItem, SalesItemTransaction, TestResult
from app.app import db
from sqlalchemy.orm import selectinload


def get_work_run_by_id(work_run_id):
    try:
        query = (
            db.session.query(WorkRun)
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise


def get_work_run_with_sales_item(work_run_id):
    """Loads work_order → sales_item → sales_item_transactions for transaction creation."""
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.work_order).selectinload(WorkOrder.sales_item)
                    .selectinload(SalesItem.sales_item_transactions)
            )
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise


def get_work_run_with_test_results(work_run_id):
    """Full fetch — loads test_results list and work_order.sales_item chain."""
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.test_results).selectinload(TestResult.test_result_items),
                selectinload(WorkRun.work_order).selectinload(WorkOrder.sales_item),
            )
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise


def get_work_runs_by_work_order(work_order_id):
    try:
        query = (
            db.session.query(WorkRun)
            .options(selectinload(WorkRun.test_results).selectinload(TestResult.test_result_items))
            .filter(WorkRun.work_order_id == work_order_id)
            .order_by(WorkRun.created_date.asc())
        )
        return query.all()
    except Exception:
        raise


def create_work_run(work_run):
    try:
        db.session.add(work_run)
        return work_run
    except Exception:
        raise
