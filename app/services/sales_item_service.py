from app.con_sqlalchemy import SalesItem, SalesItemStatus, WorkOrderStatus, SalesOrderStatus
from app.repositories import sales_item_repository, sales_order_repository
from app.app import db
from app.exception import DisabledAction, NotFoundError, ValidationError
from app.services import sales_order_service


def get_all_sales_items(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = sales_item_repository.get_all_sales_items(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise

def get_sales_item_by_id(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_by_id(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item with id {sales_item_id} not found")
        return sales_item
    except Exception:
        raise

def get_sales_item_detail(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_detail_by_id(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item with id {sales_item_id} not found")
        return sales_item
    except Exception:
        raise
def get_sales_item_tracking(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_tracking_by_id(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item with id {sales_item_id} not found")
        return sales_item
    except Exception:
        raise


def complete_sales_item(sales_item_id):
    try:
        sales_item = sales_item_repository.get_sales_item_for_complete(sales_item_id)
        if not sales_item:
            raise NotFoundError(f"Sales item {sales_item_id} not found")
        if sales_item.status == SalesItemStatus.COMPLETED:
            raise ValidationError("Sales item นี้เสร็จสิ้นแล้ว")
        completable, reason = sales_item.is_completable
        if not completable:
            raise ValidationError(reason)

        sales_item.status = SalesItemStatus.COMPLETED

        if sales_item.work_order:
            sales_item.work_order.status = WorkOrderStatus.COMPLETED

        db.session.flush()

        if sales_item.doc_entry and not sales_item_repository.has_incomplete_items_for_sales_order(sales_item.doc_entry, sales_item_id):
            sales_order = sales_order_repository.get_sales_order_by_doc_entry(sales_item.doc_entry)
            sales_order_service.sales_order_finish(sales_order)

        db.session.commit()
        return sales_item
    except Exception:
        db.session.rollback()
        raise


def create_sales_item(data):
    """Disabled. Sales items only ever come from a center push via
    sales_order_service.create_sales_order, which is the one place that sets
    produce / test / item_group / branch_id. An item built here bypasses those,
    so it lands with a NULL produce/test (NOT NULL) and, worse, an item_group that
    the Z-BOM production gate would read as unmanufactured.
    Body kept for reference until the endpoint is removed from the FE."""
    raise DisabledAction("ปิดการใช้งานการสร้าง Sales Item ผ่าน PMS แล้ว รายการขายถูกสร้างจากระบบ Center เท่านั้น")

    try:
        sales_item = SalesItem(
            item_code=data.get("item_code"),
            quantity=data.get("quantity"),
            order_line_num=data.get("order_line_num"),
            unit_name=data.get("unit_name", "Piece"),
            unit_id=data.get("unit_id"),
            item_name=data.get("item_name"),
            item_description=data.get("item_description"),
            cost_price=data.get("cost_price"),
            unit_price=data.get("unit_price"),
            doc_num=data.get("doc_num"),
        )
        sales_item = sales_item_repository.create_sales_item(sales_item)
        db.session.commit()
        return sales_item
    except Exception:
        db.session.rollback()
        raise
