import datetime
from app.con_sqlalchemy import MaterialList, SalesItem, SalesOrder, WorkOrder, WorkOrderStatus, ComponentMaterialUsage, ItemComponent, MaterialTransaction
from app.ma_sqlalchemy import WorkOrderSchema, SalesOrderSchema
from app.repositories import work_order_repository
from app.app import db
from app.services import sales_item_service
from app.exception import NotFoundError, UniqueError

def get_all_work_orders(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        filter = data.get("filter", "")
        month = data.get("month", "")
        result = work_order_repository.get_all_work_orders(page, limit, search,filter, month)
        return {"items": WorkOrderSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise

def get_sales_orders_for_qc(search="", statuses = []):
    try:
        statuses = [WorkOrderStatus(s) for s in statuses] if statuses else []
        items = work_order_repository.get_sales_orders_for_qc(search, statuses)
        return SalesOrderSchema(many=True).dump(items)
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
        sales_item_id = data.get("sales_item_id")
        item_components_data = data.get("item_components", [])

        # ตรวจสอบว่า SalesItem มีอยู่จริง
        sales_item = sales_item_service.get_sales_item_by_id(sales_item_id)

        # ตรวจสอบว่ายังไม่มี WorkOrder สำหรับ SalesItem นี้
        if sales_item.work_order:
            raise UniqueError("มี Work Order สำหรับ Sales Item นี้อยู่แล้ว")

        material_map = {m.material_list_id: m for m in sales_item.material_list}

        # Validate material availability using MaterialTransaction
        for comp in item_components_data:
            for usage in comp.get("material_usage", []):
                material_list_id = usage.get("material_list_id")
                quantity_used = usage.get("quantity_used", 0)

                if material_list_id not in material_map:
                    raise NotFoundError(f"Material ID {material_list_id} ไม่ได้อยู่ใน Sales Item นี้")

                material = material_map[material_list_id]
                total_removed = sum(t.amount for t in material.transactions if t.type == 'REMOVE')
                total_added = sum(t.amount for t in material.transactions if t.type == 'ADD')
                available = material.original_num - (total_removed - total_added)

                if quantity_used > available:
                    raise NotFoundError(
                        f"วัสดุ '{material.item_name}' (ID: {material_list_id}) ไม่เพียงพอ "
                        f"คงเหลือ: {available}, ต้องการ: {quantity_used}"
                    )

        work_order = WorkOrder(
            doc_num=sales_item.doc_num,
            doc_entry=sales_item.doc_entry,
            sales_item_id=sales_item_id,
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
        db.session.flush()

        # Create MaterialTransaction(REMOVE) for each material used
        now = datetime.datetime.now()
        for comp in item_components_data:
            for usage in comp.get("material_usage", []):
                db.session.add(MaterialTransaction(
                    material_list_id=usage.get("material_list_id"),
                    amount=usage.get("quantity_used"),
                    type="REMOVE",
                    related_document_code=work_order.doc_num or str(work_order.work_order_id),
                    created_by="System",
                    created_date=now,
                ))

        db.session.commit()
        return WorkOrderSchema().dump(work_order)
    except Exception:
        db.session.rollback()
        raise
