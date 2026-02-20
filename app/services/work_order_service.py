from app.con_sqlalchemy import MaterialList, SalesItem, SalesOrder, WorkOrder
from app.ma_sqlalchemy import WorkOrderSchema
from app.repositories import work_order_repository
from app.app import db


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
        sales_order_list = []

        for item in data.get("items", []):
            # 1) สร้าง MaterialList ก่อน
            # 2) ยัดเข้า SalesItem.material_list
            # 3) ผูก SalesItem เข้า WorkOrder ผ่าน relationship
            # SQLAlchemy cascade (save-update) จะ add ทุกอย่างให้อัตโนมัติ

            # work_order = WorkOrder(
            #     doc_num=item.get("doc_num"),
            #     doc_entry=item.get("doc_entry"),
            #     status=item.get("status", "Ready"),
            # )

            sales_order = SalesOrder(
                doc_entry = item.get("doc_entry"),
                doc_num = item.get("doc_num"),
                card_code = item.get("card_code"),
                card_name = item.get("card_name"),
                slp_code = item.get("slp_code"),
                slp_name = item.get("slp_name"),
                bpl_code = item.get("bpl_code"),
                bpl_name = item.get("bpl_name"),
                group_code = item.get("group_code"),
                group_name = item.get("group_name"),
            )

            for sale_item_data in item.get("sales_item_list", []):
                materials = [
                    MaterialList(
                        item_code=m.get("item_code"),
                        item_name=m.get("item_name"),
                        item_description=m.get("item_description"),
                        item_num=m.get("item_num"),
                        cost_price=m.get("cost_price"),
                        unit_price=m.get("unit_price"),
                    )
                    for m in sale_item_data.get("material_list", [])
                ]

                SalesItem(
                    item_code=sale_item_data.get("item_code"),
                    item_num=sale_item_data.get("item_num"),
                    item_name=sale_item_data.get("item_name"),
                    item_description=sale_item_data.get("item_description"),
                    cost_price=sale_item_data.get("cost_price"),
                    unit_price=sale_item_data.get("unit_price"),
                    doc_num=sale_item_data.get("doc_num"),
                    material_list=materials,
                    sales_order=sales_order
                )

            sales_order_list.append(sales_order)

        # add ทุก WorkOrder → cascade จะลากทุก SalesItem + MaterialList เข้า session
        db.session.add_all(sales_order_list)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise
