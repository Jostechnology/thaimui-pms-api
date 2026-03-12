from app.con_sqlalchemy import WorkRun, WorkOrder, SalesItem, TestResult
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


def get_work_run_with_test_result(work_run_id):
    """Full fetch — loads test_result and work_order.sales_item chain."""
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.test_result).selectinload(TestResult.test_result_items),
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
            .options(selectinload(WorkRun.test_result).selectinload(TestResult.test_result_items))
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
