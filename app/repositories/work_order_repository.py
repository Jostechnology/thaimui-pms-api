from app.con_sqlalchemy import WorkOrder
from app.app import db

def get_all_work_orders(page, limit, search):
    try:
        query = WorkOrder.query
        if search:
            query = query.filter(WorkOrder.doc_num.ilike(f"%{search}%"))
        query = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": query.items, "total_pages": query.pages}
    except Exception:
        raise


def create_work_order(data):
    try:
        work_order = WorkOrder(
            doc_num=data.get("doc_num"),
            status=data.get("status", "Ready"),
        )
        db.session.add(work_order)
        db.session.commit()
        return work_order
    except Exception:
        db.session.rollback()
        raise