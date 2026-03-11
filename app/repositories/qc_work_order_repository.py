from app.con_sqlalchemy import QCWorkOrder, SalesItem, SalesOrder, TestResult, TestResultItem
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.exception import NotFoundError


def _qc_work_order_options():
    """Eager-load exactly what QCWorkOrderSchema needs — no deep SalesItem nesting."""
    return [
        # Only the SalesItem scalar fields are used (item_code, item_name, doc_entry)
        selectinload(QCWorkOrder.sales_item),
        selectinload(QCWorkOrder.qc_form),
        selectinload(QCWorkOrder.qc_items),
        selectinload(QCWorkOrder.test_results)
            .selectinload(TestResult.test_result_items),
    ]


def get_all_qc_work_orders(page, limit, search, filter=None):
    try:
        query = db.session.query(QCWorkOrder)
        if search:
            query = query.filter(
                or_(
                    QCWorkOrder.qc_by.ilike(f"%{search}%"),
                    QCWorkOrder.remark.ilike(f"%{search}%"),
                )
            )
        if filter:
            query = query.filter(QCWorkOrder.qc_status == filter)
        query = query.options(selectinload(QCWorkOrder.sales_item))
        result = query.order_by(QCWorkOrder.created_date.desc()).paginate(
            page=page, per_page=limit, error_out=False
        )
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise


def get_qc_work_order_by_id(qc_work_order_id):
    try:
        qc = (
            db.session.query(QCWorkOrder)
            .options(*_qc_work_order_options())
            .filter(QCWorkOrder.qc_work_order_id == qc_work_order_id)
            .first()
        )
        if not qc:
            raise NotFoundError(f"ไม่พบ QC Work Order ID -> {qc_work_order_id}")
        return qc
    except Exception:
        raise


def create_qc_work_order(qc_work_order):
    try:
        db.session.add(qc_work_order)
        return qc_work_order
    except Exception:
        db.session.rollback()
        raise


def delete_qc_work_order(qc_work_order_id):
    try:
        qc = db.session.query(QCWorkOrder).filter(
            QCWorkOrder.qc_work_order_id == qc_work_order_id
        ).first()
        if not qc:
            raise NotFoundError(f"ไม่พบ QC Work Order ID -> {qc_work_order_id}")
        db.session.delete(qc)
        return qc
    except Exception:
        raise


def search_qc_work_orders(page, limit, search):
    try:
        query = (
            db.session.query(QCWorkOrder.qc_work_order_id, QCWorkOrder.qc_by)
            .filter(
                or_(
                    QCWorkOrder.qc_work_order_id.ilike(f"%{search}%"),
                    QCWorkOrder.qc_by.ilike(f"%{search}%")
                )
            )
            .distinct()
        )

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}

    except Exception:
        raise
