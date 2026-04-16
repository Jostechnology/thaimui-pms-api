import time

from app.api_auth import _log_timer
from app.con_sqlalchemy import WorkRun, WorkOrder, WorkRunAssignment, WorkRunMachine, WorkRunBreak, Employee, Machine, SalesItem, TestResult, TestResultWorkRun, WorkRunReworkSource, WorkRunTransaction, WorkRunRequiredItem, WorkRunPickingItem
from app.app import db
from sqlalchemy.orm import selectinload, joinedload


def get_work_run_by_id(work_run_id):
    try:
        query = (
            db.session.query(WorkRun)
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise


def get_sales_item_by_work_run(work_run_id):
    try:
        query = (
            db.session.query(SalesItem)
            .join(WorkOrder, WorkOrder.sales_item_id == SalesItem.sales_item_id)
            .join(WorkRun, WorkRun.work_order_id == WorkOrder.work_order_id)
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise


def get_work_run_display(work_run_id):
    """Full fetch — loads assignments, machines, breaks, required_items in 1 query."""
    try:
        _start = time.perf_counter()
        query = (
            db.session.query(WorkRun)
            .options(
                joinedload(WorkRun.assignments).joinedload(WorkRunAssignment.employee),
                joinedload(WorkRun.machines).joinedload(WorkRunMachine.machine),
                joinedload(WorkRun.breaks),
                joinedload(WorkRun.required_items),
            )
            .filter(WorkRun.work_run_id == work_run_id)
        )
        work_run = query.first()
        _log_timer("work_run_get", (time.perf_counter() - _start) * 1000, "", True)
        return work_run
    except Exception:
        raise


def get_work_runs_by_work_order(work_order_id):
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.test_result_sources)
                    .selectinload(TestResultWorkRun.test_result)
                    .selectinload(TestResult.test_result_items),
                selectinload(WorkRun.assignments).selectinload(WorkRunAssignment.employee),
                selectinload(WorkRun.machines).selectinload(WorkRunMachine.machine),
                selectinload(WorkRun.breaks),
                selectinload(WorkRun.rework_sources),
            )
            .filter(WorkRun.work_order_id == work_order_id)
            .order_by(WorkRun.created_date.asc())
        )
        return query.all()
    except Exception:
        raise


def get_work_runs_by_sales_item(sales_item_id):
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.test_result_sources),
                selectinload(WorkRun.rework_destinations),
            )
            .join(WorkOrder, WorkOrder.work_order_id == WorkRun.work_order_id)
            .filter(WorkOrder.sales_item_id == sales_item_id)
            .order_by(WorkRun.created_date.asc())
        )
        return query.all()
    except Exception:
        raise


def get_consumed_defect_qty_for_work_run(source_work_run_id):
    """Sum of qty already consumed from this run's defects across all rework runs."""
    try:
        query = db.session.query(
            db.func.coalesce(db.func.sum(WorkRunReworkSource.qty), 0)
        ).filter(WorkRunReworkSource.source_work_run_id == source_work_run_id)
        return query.scalar()
    except Exception:
        raise


def create_work_run(work_run):
    try:
        db.session.add(work_run)
        return work_run
    except Exception:
        raise


def create_required_item(required_item):
    db.session.add(required_item)
    return required_item


def get_required_items(work_run_id):
    query = (
        db.session.query(WorkRunRequiredItem)
        .filter(WorkRunRequiredItem.work_run_id == work_run_id)
        .order_by(WorkRunRequiredItem.id.asc())
    )
    return query.all()


def get_required_item_by_id(required_item_id):
    query = (
        db.session.query(WorkRunRequiredItem)
        .filter(WorkRunRequiredItem.id == required_item_id)
    )
    return query.first()


def create_picking_consumption(work_run_picking_item):
    db.session.add(work_run_picking_item)
    return work_run_picking_item


def get_wrpi_rows_for_required_item(work_run_required_item_id):
    """WRPI rows allocated for a specific required item, ordered FIFO ascending."""
    query = (
        db.session.query(WorkRunPickingItem)
        .filter(WorkRunPickingItem.work_run_required_item_id == work_run_required_item_id)
        .order_by(WorkRunPickingItem.picking_request_item_id.asc())
    )
    return query.all()


# --- Assignment management ---

def get_open_assignment(work_run_id, employee_id):
    """Get the open (to_time IS NULL) assignment for this employee on this run."""
    query = (
        db.session.query(WorkRunAssignment)
        .filter(
            WorkRunAssignment.work_run_id == work_run_id,
            WorkRunAssignment.employee_id == employee_id,
            WorkRunAssignment.to_time == None,
        )
    )
    return query.first()


def get_open_assignments(work_run_id):
    """All open assignments for a work run."""
    query = (
        db.session.query(WorkRunAssignment)
        .filter(
            WorkRunAssignment.work_run_id == work_run_id,
            WorkRunAssignment.to_time == None,
        )
    )
    return query.all()


def save_assignment(assignment):
    db.session.add(assignment)
    return assignment


# --- Machine management ---

def get_open_machine(work_run_id, machine_id):
    """Get the open (to_time IS NULL) machine entry for this run."""
    query = (
        db.session.query(WorkRunMachine)
        .filter(
            WorkRunMachine.work_run_id == work_run_id,
            WorkRunMachine.machine_id == machine_id,
            WorkRunMachine.to_time == None,
        )
    )
    return query.first()


def get_open_machines(work_run_id):
    """All open machine entries for a work run."""
    query = (
        db.session.query(WorkRunMachine)
        .filter(
            WorkRunMachine.work_run_id == work_run_id,
            WorkRunMachine.to_time == None,
        )
    )
    return query.all()


def save_machine_entry(machine_entry):
    db.session.add(machine_entry)
    return machine_entry


# --- Break management ---

def get_active_break(work_run_id):
    """Get the active (break_end IS NULL) break for a work run."""
    query = (
        db.session.query(WorkRunBreak)
        .filter(
            WorkRunBreak.work_run_id == work_run_id,
            WorkRunBreak.break_end == None,
        )
    )
    return query.first()


def save_break(work_run_break):
    db.session.add(work_run_break)
    return work_run_break
