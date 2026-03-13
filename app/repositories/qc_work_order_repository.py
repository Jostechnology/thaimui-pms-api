from app.con_sqlalchemy import QCWorkOrder, SalesItem, WorkOrder, WorkRun, SalesOrder
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.exception import NotFoundError


def _qc_work_order_options():
    """Eager-load exactly what QCWorkOrderSchema needs — no deep SalesItem nesting."""
    return [
        selectinload(QCWorkOrder.sales_item),
        selectinload(QCWorkOrder.qc_form),
        selectinload(QCWorkOrder.qc_items),
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


def get_qc_work_order_for_availability_check(qc_work_order_id):
    """Load QCWorkOrder → sales_item → work_order → work_runs and qc_work_orders → test_results
    so that available_for_test_qty can be computed from relations."""
    try:
        qc = (
            db.session.query(QCWorkOrder)
            .options(
                selectinload(QCWorkOrder.sales_item)
                    .selectinload(SalesItem.work_order)
                    .selectinload(WorkOrder.work_runs),
                selectinload(QCWorkOrder.sales_item)
                    .selectinload(SalesItem.qc_work_orders)
                    .selectinload(QCWorkOrder.test_results),
            )
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
