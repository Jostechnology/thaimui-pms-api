from app.con_sqlalchemy import QCWorkOrder
from app.app import db
from sqlalchemy import or_

from app.exception import NotFoundError


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
        result = query.order_by(QCWorkOrder.qc_work_order_id.desc()).paginate(
            page=page, per_page=limit, error_out=False
        )
        return {"items": result.items, "total_pages": result.pages}
    except Exception:
        raise


def get_qc_work_order_by_id(qc_work_order_id):
    try:
        qc = db.session.query(QCWorkOrder).filter(
            QCWorkOrder.qc_work_order_id == qc_work_order_id
        ).first()
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
