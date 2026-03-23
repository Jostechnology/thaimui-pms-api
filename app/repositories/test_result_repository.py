from app.con_sqlalchemy import QCWorkOrder, WorkRun, WorkOrder, SalesItem, TestResult, TestResultItem, TestResultWorkRun
from app.app import db
from sqlalchemy.orm import selectinload


def _test_result_options():
    """Eager-load what TestResultSchema needs."""
    return [
        selectinload(TestResult.test_result_items),
        selectinload(TestResult.work_run_sources).selectinload(TestResultWorkRun.work_run),
        selectinload(TestResult.picking_requests)
    ]


def _test_result_finalize_options():
    return [
        selectinload(TestResult.test_result_items),
        selectinload(TestResult.qc_work_order),
    ]


def create_test_result(test_result):
    try:
        db.session.add(test_result)
        return test_result
    except Exception:
        raise


def get_test_results_by_qc_work_order(qc_work_order_id):
    try:
        return (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .filter(TestResult.qc_work_order_id == qc_work_order_id)
            .all()
        )
    except Exception:
        raise


def get_test_result_by_id(test_result_id):
    try:
        return (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .filter(TestResult.test_result_id == test_result_id)
            .first()
        )
    except Exception:
        raise


def get_test_result_for_finalize(test_result_id):
    try:
        return (
            db.session.query(TestResult)
            .options(*_test_result_finalize_options())
            .filter(TestResult.test_result_id == test_result_id)
            .first()
        )
    except Exception:
        raise


def update_test_result(test_result):
    try:
        db.session.flush()
        db.session.refresh(test_result)
        return test_result
    except Exception:
        raise


def get_test_results_by_sales_item(sales_item_id):
    try:
        query = (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .join(QCWorkOrder, QCWorkOrder.qc_work_order_id == TestResult.qc_work_order_id)
            .filter(QCWorkOrder.sales_item_id == sales_item_id)
        )
        return query.all()
    except Exception:
        raise


def get_test_results_by_doc_entry(doc_entry):
    try:
        return (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .join(QCWorkOrder, QCWorkOrder.qc_work_order_id == TestResult.qc_work_order_id)
            .join(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
            .filter(SalesItem.doc_entry == doc_entry)
            .all()
        )
    except Exception:
        raise


def delete_test_result(test_result_id):
    try:
        test_result = get_test_result_by_id(test_result_id)
        if test_result:
            db.session.delete(test_result)
    except Exception:
        raise


def get_reworked_qty_for_test_result(test_result_id):
    """Sum of qty_from_failed across all rework WorkRuns sourced from this test result."""
    try:
        query = db.session.query(
            db.func.coalesce(db.func.sum(WorkRun.qty_from_failed), 0)
        ).filter(WorkRun.rework_source_test_result_id == test_result_id)
        return query.scalar()
    except Exception:
        raise


def get_committed_qty_for_work_run(work_run_id, exclude_test_result_id=None):
    """Sum of qty_from_run already committed for a work_run across all test results."""
    try:
        query = db.session.query(
            db.func.coalesce(db.func.sum(TestResultWorkRun.qty_from_run), 0)
        ).filter(TestResultWorkRun.work_run_id == work_run_id)
        if exclude_test_result_id:
            query = query.filter(TestResultWorkRun.test_result_id != exclude_test_result_id)
        return query.scalar()
    except Exception:
        raise
