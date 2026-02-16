from app.con_sqlalchemy import WorkOrder
from app.app import db
from sqlalchemy import or_


def search_sales_order(page, limit, search):
    try:
        query = (
            db.session.query(WorkOrder.doc_entry, WorkOrder.doc_num)
            .filter(
                or_(
                    WorkOrder.doc_entry.ilike(f"%{search}%"),
                    WorkOrder.doc_num.ilike(f"%{search}%")
                )
            )
            .distinct()
        )

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return result.items

    except Exception:
        raise

