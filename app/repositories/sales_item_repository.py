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


def create_sales_item(data):
    try:
        sales_item = SalesItem(
            item_code=data.get("item_code"),
            item_num=data.get("item_num"),
            item_name=data.get("item_name"),
            item_description=data.get("item_description"),
            cost_price=data.get("cost_price"),
            unit_price=data.get("unit_price"),
            doc_num=data.get("doc_num"),
        )
        db.session.add(sales_item)
        db.session.commit()
        return sales_item
    except Exception:
        db.session.rollback()
        raise
