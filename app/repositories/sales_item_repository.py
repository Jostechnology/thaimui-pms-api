from app.con_sqlalchemy import SalesItem, MaterialList, WorkOrder, QCWorkOrder, SalesItemTransaction, TestResult
from app.app import db
from sqlalchemy.orm import selectinload

def get_all_sales_items(page, limit, search):
    try:
        query = SalesItem.query
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
        return SalesItem.query.get(sales_item_id)
    except Exception:
        raise


def get_sales_item_detail_by_id(sales_item_id):
    """Full fetch with all nested data for SalesItemDetailSchema serialization."""
    try:
        return (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.material_list),
                selectinload(SalesItem.work_order),
                selectinload(SalesItem.qc_work_orders),
                selectinload(SalesItem.sales_item_transactions),
            )
            .filter(SalesItem.sales_item_id == sales_item_id)
            .first()
        )
    except Exception:
        raise

def get_sales_item_tracking_by_id(sales_item_id):
    """Fetch sales item with work order phases and QC work order test results for tracking."""
    try:
        query = (
            db.session.query(SalesItem)
            .options(
                selectinload(SalesItem.work_order).selectinload(WorkOrder.current_phase),
                selectinload(SalesItem.work_order).selectinload(WorkOrder.work_phases),
                selectinload(SalesItem.qc_work_orders).selectinload(QCWorkOrder.test_results),
            )
            .filter(SalesItem.sales_item_id == sales_item_id)
        )
        return query.first()
    except Exception:
        raise


def get_sales_items_by_doc_entry(doc_entry):
    try:
        return (
            db.session.query(SalesItem)
            .filter(SalesItem.doc_entry == doc_entry)
            .order_by(SalesItem.sales_item_id)
            .all()
        )
    except Exception:
        raise