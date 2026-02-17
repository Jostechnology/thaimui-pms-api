from app.con_sqlalchemy import SalesOrder
from app.app import db
from sqlalchemy import or_

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

def get_sales_order_detail(doc_entry):
    try:
        sales_order = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry).first()
        if not sales_order:
            raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
        return sales_order
    except Exception:
        raise
