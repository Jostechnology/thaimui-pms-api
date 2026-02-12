from app.ma_sqlalchemy import SalesItemSchema
from app.repositories import sales_item_repository


def get_all_sales_items(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = sales_item_repository.get_all_sales_items(page, limit, search)
        return {"items": SalesItemSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise


def create_sales_item(data):
    try:
        sales_item = sales_item_repository.create_sales_item(data)
        return SalesItemSchema().dump(sales_item)
    except Exception:
        raise
