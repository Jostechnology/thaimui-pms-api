from app.ma_sqlalchemy import WorkOrderSchema
from app.repositories import material_list_repository, work_order_repository, sales_item_repository
from app.app import db


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
        work_order_list = []
        for item in data.get("items", []):
            for sale_item in item.get("sales_item_list", []):
                new_sale_item = sales_item_repository.create_sales_item(sale_item)
                work_order = work_order_repository.create_work_order(item)
                new_sale_item.work_order_id = work_order.work_order_id
                for material in sale_item.get("material_list", []):
                    sale_item_id = new_sale_item.sales_item_id
                    material["sales_item_id"] = sale_item_id
                    new_material = material_list_repository.create_material_list(material)
                    new_sale_item.material_list.append(new_material)
                work_order_list.append(work_order)
        db.session.commit()
        return WorkOrderSchema(many=True).dump(work_order_list)
    except Exception:
        db.session.rollback()
        raise
