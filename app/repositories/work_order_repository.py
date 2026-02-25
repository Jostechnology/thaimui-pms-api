from app.con_sqlalchemy import WorkOrder, WorkOrderStatus, SalesOrder
from app.app import db
from sqlalchemy import extract, or_

def get_all_work_orders(page, limit, search,filter, month):
    try:
        query = WorkOrder.query
        if search:
            query = query.filter(WorkOrder.doc_num.ilike(f"%{search}%"))
        if filter:
            query = query.filter(WorkOrder.status == filter)
        if month:
            filter_year, filter_month = map(int, month.split('-'))
            query = query.filter(
                extract('year', WorkOrder.created_date) == filter_year,
                extract('month', WorkOrder.created_date) == filter_month
            )
        query = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": query.items, "total_pages": query.pages}
    except Exception:
        raise

def get_work_order_by_id(work_order_id):
    try:
        work_order = WorkOrder.query.get(work_order_id)
        return work_order
    except Exception:
        raise

def get_sales_orders_for_qc(search=""):
    """ดึง SalesOrder ที่ผูกกับ WorkOrder สถานะ WAIT_TEST หรือ TESTING เท่านั้น"""
    try:
        query = (
            db.session.query(SalesOrder)
            .join(WorkOrder, WorkOrder.doc_entry == SalesOrder.doc_entry)
            .filter(
                or_(
                    WorkOrder.status == WorkOrderStatus.WAIT_TEST,
                    WorkOrder.status == WorkOrderStatus.TESTING,
                )
            )
        )
        if search:
            query = query.filter(
                or_(
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                )
            )
        return query.order_by(SalesOrder.doc_entry.desc()).all()
    except Exception:
        raise
