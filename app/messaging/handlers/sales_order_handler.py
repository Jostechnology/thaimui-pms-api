from app.exception import MissingFieldsError
from app.services import sales_order_service


def handle_create_sales_order(payload):
    data = payload.get("items", [])
    if not data:
        raise MissingFieldsError("ไม่พบรายการใบสั่งขายที่ต้องส่งมา")
    sales_order_service.create_sales_order_routine(data)