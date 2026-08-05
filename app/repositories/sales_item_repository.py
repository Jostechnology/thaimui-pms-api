from app.con_sqlalchemy import SalesItem, MaterialList, WorkOrder, WorkRun, QCWorkOrder, TestResult, SalesItemStatus, PickingRequestItem, PickingRequest
from app.app import db
from sqlalchemy.orm import joinedload, selectinload

# QCWorkOrder.test_spec is lazy='noload' and SalesItem.unavailable_for_test_qty
# scopes its pool to DIRECT-sourced QCs — every eager-load of
# SalesItem.qc_work_orders below must also load test_spec, or that property
# (and available_for_test_qty) silently misclassifies every QC as DIRECT and
# reports the wrong number.

def get_all_sales_items(page, limit, search):
    try:
        query = (
            db.session.query(SalesItem)
            .options(
                joinedload(SalesItem.work_order).selectinload(WorkOrder.work_runs),
                joinedload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
                joinedload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_spec),
                selectinload(SalesItem.picking_request_items).joinedload(PickingRequestItem.picking_request),
            )
        )
        if search:
            query = query.filter(
                db.or_(
                    SalesItem.item_code.ilike(f"%{search}%"),
                    SalesItem.item_name.ilike(f"%{search}%"),
                    SalesItem.doc_num.ilike(f"%{search}%"),
                )
            )
        query = query.order_by(SalesItem.created_date.desc())
        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise


def get_sales_item_by_id(sales_item_id):
    """Lightweight fetch — no eager loading. Use for write operations."""
    try:
        query = db.session.query(SalesItem).filter(SalesItem.sales_item_id == sales_item_id)
        return query.first()
    except Exception:
        raise

def get_sales_item_order_in_sales_order(sales_item_id, doc_entry):
    """Return the 1-based position of sales_item_id among items in the same sales order, ordered by sales_item_id."""
    try:
        query = db.session.query(SalesItem).filter(
            SalesItem.doc_entry == doc_entry,
            SalesItem.sales_item_id <= sales_item_id
        )
        return query.count()
    except Exception:
        raise


def get_sales_item_detail_by_id(sales_item_id):
    try:
        return (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.material_list),
                selectinload(SalesItem.work_order).selectinload(WorkOrder.work_runs),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_spec),
                selectinload(SalesItem.picking_request_items).selectinload(PickingRequestItem.picking_request),
            )
            .filter(SalesItem.sales_item_id == sales_item_id)
            .first()
        )
    except Exception:
        raise

def get_sales_item_tracking_by_id(sales_item_id):
    """Fetch sales item with work order → work runs, and qc_work_orders → test_results (simple)."""
    try:
        query = (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.work_order).selectinload(WorkOrder.work_runs),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_spec),
                selectinload(SalesItem.picking_request_items).selectinload(PickingRequestItem.picking_request),
            )
            .filter(SalesItem.sales_item_id == sales_item_id)
        )
        return query.first()
    except Exception:
        raise


def get_sales_item_for_complete(sales_item_id):
    """Load work_order → work_runs (for produced_qty) and qc_work_orders (for is_completable)."""
    try:
        query = (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.work_order).selectinload(WorkOrder.work_runs),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_spec),
            )
            .filter(SalesItem.sales_item_id == sales_item_id)
        )
        return query.first()
    except Exception:
        raise


def has_incomplete_items_for_sales_order(doc_entry, exclude_sales_item_id):
    """Return True if any sibling SalesItem (excluding current) is not yet COMPLETED."""
    query = db.session.query(SalesItem).filter(
        SalesItem.doc_entry == doc_entry,
        SalesItem.sales_item_id != exclude_sales_item_id,
        SalesItem.status != SalesItemStatus.COMPLETED,
    )
    return query.first() is not None


def has_incomplete_items(doc_entry):
    """Return True if any SalesItem for this order is not yet COMPLETED."""
    query = db.session.query(SalesItem).filter(
        SalesItem.doc_entry == doc_entry,
        SalesItem.status != SalesItemStatus.COMPLETED,
    )
    return query.first() is not None


def get_sales_items_by_doc_entry(doc_entry):
    """Items of one order with the relationships that is_completable / production_blocker
    read. Without these eager loads the lazy='noload' relationships read as empty and the
    computed properties silently report wrong numbers."""
    try:
        query = (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.material_list),
                selectinload(SalesItem.work_order).selectinload(WorkOrder.work_runs),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_spec),
                selectinload(SalesItem.picking_request_items).selectinload(PickingRequestItem.picking_request),
            )
            .filter(SalesItem.doc_entry == doc_entry)
            .order_by(SalesItem.sales_item_id)
        )
        return query.all()
    except Exception:
        raise