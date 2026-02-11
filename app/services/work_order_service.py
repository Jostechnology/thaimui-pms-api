from app.ma_sqlalchemy import WorkOrderSchema
from app.repositories import work_order_repository


def get_all_work_orders(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = work_order_repository.get_all_work_orders(page, limit, search)
        return {"items": WorkOrderSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise


def create_work_order(data):
    try:
        work_order = work_order_repository.create_work_order(data)
        return WorkOrderSchema().dump(work_order)
    except Exception:
        raise
