from app.con_sqlalchemy import QCWorkOrder, WorkRun, WorkOrder, SalesItem, SalesItemTransaction, TestResult, TestResultItem
from app.app import db
from sqlalchemy.orm import selectinload


def _test_result_options():
    """Eager-load what TestResultSchema needs."""
    return [
        selectinload(TestResult.test_result_items),
        selectinload(TestResult.work_run),
    ]


def _test_result_finalize_options():
    """Full chain needed for finalize — sales_item transactions for IN_TESTING write."""
    return [
        selectinload(TestResult.test_result_items),
        selectinload(TestResult.qc_work_order)
            .selectinload(QCWorkOrder.sales_item)
            .selectinload(SalesItem.sales_item_transactions),
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
            .order_by(TestResult.test_result_id.desc())
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


def get_test_results_by_doc_entry(doc_entry):
    try:
        return (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .join(QCWorkOrder, QCWorkOrder.qc_work_order_id == TestResult.qc_work_order_id)
            .join(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
            .filter(SalesItem.doc_entry == doc_entry)
            .order_by(TestResult.test_result_id.desc())
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
