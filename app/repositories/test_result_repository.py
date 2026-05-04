from app.con_sqlalchemy import PickingRequestItem, QCWorkOrder, WorkRun, WorkOrder, SalesItem, TestResult, TestResultItem, TestResultWorkRun, TestResultPickingItem, TestResultRequiredItem, TestResultAssignment, TestResultMachine, TestResultBreak
from app.app import db
from sqlalchemy.orm import joinedload, selectinload


def _test_result_options():
    """Eager-load what TestResultSchema needs."""
    return [
        selectinload(TestResult.test_result_items),
        joinedload(TestResult.work_run_sources).joinedload(TestResultWorkRun.work_run),
        selectinload(TestResult.picking_item_sources).selectinload(TestResultPickingItem.picking_request_item).joinedload(PickingRequestItem.picking_request),
        selectinload(TestResult.required_items).joinedload(TestResultRequiredItem.material_list),
        selectinload(TestResult.assignments).joinedload(TestResultAssignment.employee),
        selectinload(TestResult.machines).joinedload(TestResultMachine.machine),
        selectinload(TestResult.breaks),
        joinedload(TestResult.cost),
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
        query = (
            db.session.query(TestResult)
            .options(
                selectinload(TestResult.test_result_items),
                joinedload(TestResult.work_run_sources).joinedload(TestResultWorkRun.work_run),
                joinedload(TestResult.picking_item_sources).joinedload(TestResultPickingItem.picking_request_item).joinedload(PickingRequestItem.picking_request),
                selectinload(TestResult.required_items).joinedload(TestResultRequiredItem.material_list)
            )
            .filter(TestResult.qc_work_order_id == qc_work_order_id)
        )
        return query.all()
    except Exception:
        raise


def get_test_results_cost_by_qc_work_order(qc_work_order_id):
    try:
        query = (
            db.session.query(TestResult)
            .options(*_test_result_options())
            .filter(TestResult.qc_work_order_id == qc_work_order_id)
        )
        return query.all()
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


def get_sales_item_by_test_result(test_result_id):
    try:
        query = (
            db.session.query(SalesItem)
            .join(QCWorkOrder, QCWorkOrder.sales_item_id == SalesItem.sales_item_id)
            .join(TestResult, TestResult.qc_work_order_id == QCWorkOrder.qc_work_order_id)
            .filter(TestResult.test_result_id == test_result_id)
        )
        return query.first()
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


def get_required_items(test_result_id):
    """All TestResultRequiredItem rows for a TestResult, ordered by id."""
    query = (
        db.session.query(TestResultRequiredItem)
        .filter(TestResultRequiredItem.test_result_id == test_result_id)
        .order_by(TestResultRequiredItem.id.asc())
    )
    return query.all()


def get_required_item_by_id(required_item_id):
    query = (
        db.session.query(TestResultRequiredItem)
        .filter(TestResultRequiredItem.id == required_item_id)
    )
    return query.first()


def get_trpi_rows_for_required_item(test_result_required_item_id):
    """TRPI rows allocated for a specific required item, ordered FIFO ascending."""
    query = (
        db.session.query(TestResultPickingItem)
        .filter(TestResultPickingItem.test_result_required_item_id == test_result_required_item_id)
        .order_by(TestResultPickingItem.picking_request_item_id.asc())
    )
    return query.all()


# --- Assignment management ---

def get_open_assignment(test_result_id, employee_id):
    query = (
        db.session.query(TestResultAssignment)
        .filter(
            TestResultAssignment.test_result_id == test_result_id,
            TestResultAssignment.employee_id == employee_id,
            TestResultAssignment.to_time == None,
        )
    )
    return query.first()


def save_assignment(assignment):
    db.session.add(assignment)
    return assignment


# --- Machine management ---

def get_open_machine(test_result_id, machine_id):
    query = (
        db.session.query(TestResultMachine)
        .filter(
            TestResultMachine.test_result_id == test_result_id,
            TestResultMachine.machine_id == machine_id,
            TestResultMachine.to_time == None,
        )
    )
    return query.first()


def save_machine_entry(machine_entry):
    db.session.add(machine_entry)
    return machine_entry


# --- Break management ---

def save_break(test_result_break):
    db.session.add(test_result_break)
    return test_result_break


def get_active_break(test_result_id):
    """Return the open break (break_end IS NULL) for a test result, or None."""
    query = (
        db.session.query(TestResultBreak)
        .filter(
            TestResultBreak.test_result_id == test_result_id,
            TestResultBreak.break_end == None,
        )
    )
    return query.first()


def get_all_breaks(test_result_id):
    query = (
        db.session.query(TestResultBreak)
        .filter(TestResultBreak.test_result_id == test_result_id)
        .order_by(TestResultBreak.break_start)
    )
    return query.all()
