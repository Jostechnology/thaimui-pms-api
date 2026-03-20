from app.con_sqlalchemy import WorkRun, WorkOrder, WorkPhase, WorkAssignment, SalesItem, TestResult, TestResultWorkRun, WorkRunReworkSource, WorkRunTransaction
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



def get_work_run_with_test_results(work_run_id):
    """Full fetch — loads test_result_sources, work_phases, rework_sources, rework_destinations, transactions."""
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.test_result_sources)
                    .selectinload(TestResultWorkRun.test_result)
                    .selectinload(TestResult.test_result_items),
                selectinload(WorkRun.work_order).selectinload(WorkOrder.sales_item),
                selectinload(WorkRun.work_phases)
                    .selectinload(WorkPhase.assignments)
                    .selectinload(WorkAssignment.employee),
                selectinload(WorkRun.work_phases).selectinload(WorkPhase.breaks),
                selectinload(WorkRun.current_phase),
                selectinload(WorkRun.rework_sources),
                selectinload(WorkRun.rework_destinations),
                selectinload(WorkRun.transactions),
            )
            .filter(WorkRun.work_run_id == work_run_id)
        )
        return query.first()
    except Exception:
        raise

def get_work_run_display(work_run_id):
    """Full fetch — loads test_result_sources, work_phases, rework_sources, rework_destinations, transactions."""
    try:
        query = (
            db.session.query(WorkRun)
            .options(
                selectinload(WorkRun.work_order).selectinload(WorkOrder.sales_item),
                selectinload(WorkRun.work_phases)
                    .selectinload(WorkPhase.assignments)
                    .selectinload(WorkAssignment.employee),
                selectinload(WorkRun.work_phases).selectinload(WorkPhase.breaks),
                selectinload(WorkRun.current_phase),
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
            .options(
                selectinload(WorkRun.test_result_sources)
                    .selectinload(TestResultWorkRun.test_result)
                    .selectinload(TestResult.test_result_items),
                selectinload(WorkRun.work_phases)
                    .selectinload(WorkPhase.assignments)
                    .selectinload(WorkAssignment.employee),
                selectinload(WorkRun.work_phases).selectinload(WorkPhase.breaks),
                selectinload(WorkRun.current_phase),
                selectinload(WorkRun.rework_sources),
                selectinload(WorkRun.rework_destinations),
                selectinload(WorkRun.transactions),
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
