from app.ma_sqlalchemy import WorkOrderSchema
from app.repositories import work_order_repository
from app.app import db
from app.services import sales_item_service
from app.con_sqlalchemy import ComponentMaterialUsage, ItemComponent, WorkOrder
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

        # สร้าง map ของ material_list ที่อยู่ใน SalesItem นี้
        material_map = {m.material_list_id: m for m in sales_item.material_list}

        # ตรวจสอบว่า material แต่ละตัวอยู่ใน SalesItem และมีจำนวนเพียงพอ
        for comp in item_components_data:
            material_list_id = comp.get("material_list_id")
            quantity_used = comp.get("quantity_used", 0)

            if material_list_id not in material_map:
                raise NotFoundError(
                    f"Material ID {material_list_id} ไม่ได้อยู่ใน Sales Item นี้"
                )

            material = material_map[material_list_id]
            # คำนวณจำนวนที่ถูกใช้ไปแล้วจาก WorkOrder อื่น
            already_used = sum(
                usage.quantity_used for usage in material.component_usages
            )
            available = material.item_num - already_used
            if quantity_used > available:
                raise NotFoundError(
                    f"วัสดุ '{material.item_name}' (ID: {material_list_id}) ไม่เพียงพอ "
                    f"คงเหลือ: {available}, ต้องการ: {quantity_used}"
                )
            material.item_num -= quantity_used  # อัปเดตจำนวนคงเหลือใน MaterialList

        # สร้าง WorkOrder
        work_order = WorkOrder(
            doc_num=sales_item.doc_num,
            doc_entry=sales_item.doc_entry,
            sales_item_id=sales_item_id,
        )

        # สร้าง ItemComponent + ComponentMaterialUsage
        for comp in item_components_data:
            item_component = ItemComponent()
            work_order.item_components.append(item_component)

            material_usage = ComponentMaterialUsage(
                material_list_id=comp.get("material_list_id"),
                quantity_used=comp.get("quantity_used"),
            )
            item_component.material_usages.append(material_usage)

        db.session.add(work_order)
        db.session.commit()
        return WorkOrderSchema().dump(work_order)
    except Exception:
        db.session.rollback()
        raise
