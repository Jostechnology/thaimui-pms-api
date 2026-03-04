from app.exception import OuterServicesError
from app.ma_sqlalchemy import SalesOrderSearchSchema
from app.repositories import sales_order_repository
from app.extensions import center_service
from app.app import db
from app.services import work_order_service


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

def get_all_sales_orders(data):
    try:
        from app.ma_sqlalchemy import SalesOrderListSchema
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        
        result = sales_order_repository.get_all_sales_orders(page, limit, search)
        items = SalesOrderListSchema(many=True).dump(result.items)
        
        return {
            "items": items,
            "total_pages": result.pages,
            "total_items": result.total,
            "current_page": result.page
        }
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
        print("====== RAW RESPONSE JSON ======")
        print(response)
        print("===============================")
        data = {"items" : response["json"]}
        print(data)
        work_order_service.create_work_order(data)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
