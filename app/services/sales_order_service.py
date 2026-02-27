from app.ma_sqlalchemy import SalesOrderSearchSchema
from app.repositories import sales_order_repository
from app.extensions import center_service
from app.app import db
from app.services import work_order_service
from app.con_sqlalchemy import SalesOrder, SalesItem, MaterialList


def search_sales_order(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = sales_order_repository.search_sales_order(page, limit, search)
        sales_orders = SalesOrderSearchSchema(many=True).dump(result)
        return sales_orders
    except Exception:
        raise

def get_sales_order_detail(doc_entry):
    try:
        result = sales_order_repository.get_sales_order_detail(doc_entry)
        items = result.sales_items
        
        materials = []
        for i in items:
            materials.extend(i.material_list)
        return result, items, materials
    except Exception:
        db.session.rollback()
        raise

def get_test_sales_order():
    try:
        response = center_service.request(
            method="POST",
            endpoint="/api/ORDR/get_test_quick",
        )
        data = {"items" : response["json"]}
        print(data)
        create_sales_order(data)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
def create_sales_order(data):
    try:

        sales_order = SalesOrder(
            doc_entry = data.get("doc_entry"),
            doc_num = data.get("doc_num"),
            card_code = data.get("card_code"),
            card_name = data.get("card_name"),
            slp_code = data.get("slp_code"),
            slp_name = data.get("slp_name"),
            bpl_code = data.get("bpl_code"),
            bpl_name = data.get("bpl_name"),
            group_code = data.get("group_code"),
            group_name = data.get("group_name"),
        )

        for item in data.get("sales_item_list", []):
            sales_item = SalesItem(
                item_code=item.get("item_code"),
                item_name=item.get("item_name"),
                item_num=item.get("item_num"),
                unit_price=item.get("unit_price"),
                cost_price=item.get("cost_price")
            )
            sales_order.sales_items.append(sales_item)

            for mat in item.get("material_list", []):
                material_list = MaterialList(
                    item_code=mat.get("item_code"),
                    item_name=mat.get("item_name"),
                    item_description=mat.get("item_description"),
                    item_num=mat.get("item_num"),
                    unit_price=mat.get("unit_price"),
                    cost_price=mat.get("cost_price")
                )
                sales_item.material_list.append(material_list)

        db.session.add(sales_order)
        return sales_order
    except Exception:
        db.session.rollback()
        raise