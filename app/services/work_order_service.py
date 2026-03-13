from app.con_sqlalchemy import MaterialList, SalesItem, SalesOrder, WorkOrder, WorkRun, WorkRunStatus, ComponentMaterialUsage, ItemComponent, SalesItemTransactionType
from app.repositories import work_order_repository
from app.app import db
from app.services import sales_item_service, transaction_service
from app.exception import NotFoundError, UniqueError

def get_all_work_orders(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        filter = data.get("filter", "")
        month = data.get("month", "")
        result = work_order_repository.get_all_work_orders(page, per_page, search,filter, month)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise

def get_work_order_by_id(work_order_id):
    try:
        work_order = work_order_repository.get_work_order_by_id(work_order_id)
        return work_order
    except Exception:
        raise

def create_work_order(data):
    try:
        sales_item_id = data.get("sales_item_id")
        item_components_data = data.get("item_components", [])

        # ตรวจสอบว่า SalesItem มีอยู่จริง
        sales_item = sales_item_service.get_sales_item_by_id(sales_item_id)

        if sales_item.work_order:
            raise UniqueError("มี Work Order สำหรับ Sales Item นี้อยู่แล้ว")

        quantity = data.get("quantity") or sales_item.item_num

        material_map = {m.material_list_id: m for m in sales_item.material_list}

        # Validate that all materials belong to this SalesItem
        for comp in item_components_data:
            for usage in comp.get("material_usage", []):
                if usage.get("material_list_id") not in material_map:
                    raise NotFoundError(f"Material ID {usage.get('material_list_id')} ไม่ได้อยู่ใน Sales Item นี้")

        work_order = WorkOrder(
            doc_num=sales_item.doc_num,
            doc_entry=sales_item.doc_entry,
            sales_item_id=sales_item_id,
            quantity=quantity,
        )

        # Create ItemComponent + ComponentMaterialUsage
        for comp in item_components_data:
            item_component = ItemComponent(component_name=comp.get("component_name", ""))
            work_order.item_components.append(item_component)

            for usage in comp.get("material_usage", []):
                material_usage = ComponentMaterialUsage(
                    material_list_id=usage.get("material_list_id"),
                    quantity_used=usage.get("quantity_used"),
                )
                item_component.material_usages.append(material_usage)

        db.session.add(work_order)

        db.session.commit()
        return work_order
    except Exception:
        db.session.rollback()
        raise
