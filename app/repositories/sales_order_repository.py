from app.con_sqlalchemy import SalesOrder, SalesItem, WorkOrder, QCCertification, QCCheckItem, MaterialList
from app.app import db
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from app.exception import NotFoundError


def search_sales_order(page, limit, search):
    try:
        query = (
            db.session.query(SalesOrder.doc_entry, SalesOrder.doc_num)
            .filter(
                or_(
                    SalesOrder.doc_entry.ilike(f"%{search}%"),
                    SalesOrder.doc_num.ilike(f"%{search}%")
                )
            )
            .distinct()
        )

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return result.items

    except Exception:
        raise

def get_all_sales_orders(page, limit, search):
    try:
        sales_items_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        work_orders_subq = (
            db.session.query(func.count(WorkOrder.work_order_id))
            .join(SalesItem, WorkOrder.sales_item_id == SalesItem.sales_item_id)
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        query = db.session.query(
            SalesOrder,
            sales_items_subq.label("sales_items_count"),
            work_orders_subq.label("work_orders_count"),
        )

        if search:
            query = query.filter(
                or_(
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(SalesOrder.doc_num.desc())
        return query.paginate(page=page, per_page=limit, error_out=False)
    except Exception:
        raise


def get_sales_order_detail(doc_entry):
    try:
        sales_order = (
            db.session.query(SalesOrder)
            .options(
                # Load sales_items → material_list only; no transactions, no work_order chain
                selectinload(SalesOrder.sales_items)
                    .selectinload(SalesItem.material_list),
                # Load certifications → check_items only
                selectinload(SalesOrder.certifications)
                    .selectinload(QCCertification.check_items),
            )
            .filter(SalesOrder.doc_entry == doc_entry)
            .first()
        )
        if not sales_order:
            raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
        return sales_order
    except Exception:
        raise

