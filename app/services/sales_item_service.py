from app.con_sqlalchemy import SalesItem
from app.ma_sqlalchemy import SalesItemSchema, SalesItemDetailSchema
from app.repositories import sales_item_repository
from app.app import db
from app.exception import NotFoundError


def get_all_sales_items(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = sales_item_repository.get_all_sales_items(page, limit, search)
        return {"items": SalesItemSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise

def get_sales_item_by_id(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_by_id(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item with id {sales_item_id} not found")
        return sales_item
    except Exception:
        raise

def get_sales_item_detail(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_detail_by_id(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item with id {sales_item_id} not found")
        return SalesItemDetailSchema().dump(sales_item)
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
        sales_item = sales_item_repository.create_sales_item(sales_item)
        db.session.commit()
        return SalesItemSchema().dump(sales_item)
    except Exception:
        db.session.rollback()
        raise
