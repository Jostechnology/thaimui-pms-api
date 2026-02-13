from app.con_sqlalchemy import MaterialList, SalesItem, WorkOrder
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

def get_work_order_by_id(work_order_id):
    try:
        work_order = work_order_repository.get_work_order_by_id(work_order_id)
        return WorkOrderSchema().dump(work_order)
    except Exception:
        raise

def create_work_order(data):
    try:
        work_order_list = []
        for item in data.get("items", []):
            work_order = WorkOrder(
                doc_num=item.get("doc_num"),
                doc_entry=item.get("doc_entry"),
                status=item.get("status", "Ready"),
            )
            work_order = work_order_repository.create_work_order(work_order)
            for sale_item in item.get("sales_item_list", []):
                new_sale_item = SalesItem(
                    item_code=sale_item.get("item_code"),
                    item_num=sale_item.get("item_num"),
                    item_name=sale_item.get("item_name"),
                    item_description=sale_item.get("item_description"),
                    cost_price=sale_item.get("cost_price"),
                    unit_price=sale_item.get("unit_price"),
                    doc_num=sale_item.get("doc_num"),
                    work_order_id=work_order.work_order_id,
                )
                new_sale_item = sales_item_repository.create_sales_item(new_sale_item)
                for material in sale_item.get("material_list", []):
                    new_material = MaterialList(
                        sales_item_id=new_sale_item.sales_item_id,
                        item_code=material.get("item_code"),
                        item_name=material.get("item_name"),
                        item_description=material.get("item_description"),
                        item_num=material.get("item_num"),
                        cost_price=material.get("cost_price"),
                        unit_price=material.get("unit_price"),
                    )
                    material_list_repository.create_material_list(new_material)
            work_order_list.append(work_order)
        db.session.commit()
        return WorkOrderSchema(many=True).dump(work_order_list)
    except Exception:
        db.session.rollback()
        raise
