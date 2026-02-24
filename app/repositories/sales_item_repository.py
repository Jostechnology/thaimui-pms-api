from app.con_sqlalchemy import SalesItem
from app.app import db


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
        return {"items": result.items, "total_pages": result.pages}
    except Exception:
        raise
def get_sales_item_by_id(sales_item_id):
    try:
        sales_item = SalesItem.query.get(sales_item_id)
        return sales_item
    except Exception:
        raise