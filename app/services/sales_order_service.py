from app.exception import OuterServicesError
from app.ma_sqlalchemy import SalesItemSchema, SalesOrderSearchSchena
from app.repositories import sales_order_repository
from app.extensions import center_service
from app.app import db


def search_sales_order(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = sales_order_repository.search_sales_order(page, limit, search)
        sales_orders = SalesOrderSearchSchena(many=True).dump(result)
        return sales_orders
    except Exception:
        raise

def get_sales_order_detail(doc_entry):
    try:
        response = center_service.request(
            method="POST",
            endpoint="/api/ORDR/fetch",
            data={"doc_entry": doc_entry}
        )
        print(response)
        if response["status_code"] != 200:
            raise OuterServicesError(f"เกิดข้อผิดพลาดในการทำงานกับ Center service : {response['json']}")
        return response['json']
    except Exception:
        db.session.rollback()
        raise
