import logging

from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem,
    PickingRequestStatus,
)
from app.repositories import picking_request_repository, sales_order_repository
from app.services import document_code_service
from app.app import db
from app.exception import ManualRaiseToTest, NotFoundError, ValidationError, OuterServicesError
from app.extensions import wms_service
from app.utils import convert_start_date, convert_end_date

logger = logging.getLogger(__name__)


def _build_items(items_data):
    """Validate and build PickingRequestItem objects from request payload."""
    if not items_data:
        raise ValidationError("ต้องระบุรายการสินค้า (items) อย่างน้อย 1 รายการ")

    result = []
    for i, item in enumerate(items_data):
        item_code = item.get("item_code", "").strip()
        item_name = item.get("item_name", "").strip()
        quantity = item.get("quantity")

        if not item_code:
            raise ValidationError(f"รายการที่ {i + 1}: item_code ไม่ถูกต้อง")
        if not item_name:
            raise ValidationError(f"รายการที่ {i + 1}: item_name ไม่ถูกต้อง")
        if not quantity or quantity <= 0:
            raise ValidationError(f"รายการที่ {i + 1}: quantity ต้องมากกว่า 0")

        result.append(PickingRequestItem(
            item_code=item_code,
            item_name=item_name,
            quantity=quantity,
            unit=item.get("unit"),
            remark=item.get("remark"),
            order_line_num=item.get("order_line_num"),
            sales_item_id=item.get("sales_item_id"),
            material_list_id=item.get("material_list_id"),
        ))
    return result


def _build_wms_order_items(items):
    """
    Consolidate PickingRequestItems into WMS lines, merging by item_code + unit.

    Same item_code can appear from multiple sources:
    - Same material in different SalesItems' MaterialLists
    - A non-produced SalesItem with the same item_code as another SalesItem's material

    WMS only needs one line per item_code with total quantity.
    order_line_num sent is the lowest one in the group (first in BOM order).
    """
    consolidated = {}
    for item in items:
        key = (item.item_code, item.unit or "")
        if key not in consolidated:
            consolidated[key] = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "unit": item.unit,
                "quantity": 0,
                "order_line_num": item.order_line_num,  # first seen = lowest
            }
        consolidated[key]["quantity"] += item.quantity
        # keep smallest order_line_num (None is treated as largest)
        existing_ln = consolidated[key]["order_line_num"]
        if item.order_line_num is not None:
            if existing_ln is None or item.order_line_num < existing_ln:
                consolidated[key]["order_line_num"] = item.order_line_num

    return [
        {
            "order_line_num": v["order_line_num"],
            "item_code": v["item_code"],
            "item_name": v["item_name"],
            "unit": v["unit"],
            "quantity": v["quantity"],
        }
        for v in consolidated.values()
        if v["order_line_num"] is not None
    ]


def _call_wms_create_pickup(pr, items):
    """
    Call WMS create_pickup_from_pms if the service is configured.
    Consolidates items by item_code before sending (same material across multiple lines → 1 WMS line).
    On success: set pr.status = SENT, pr.wms_reference = pickup_id.
    On failure (success=False or exception): raise OuterServicesError.
    """
    if wms_service is None:
        return

    order_items = _build_wms_order_items(items)

    if not order_items:
        return

    try:
        resp = wms_service.create_pickup_from_pms(
            picking_request_code=pr.picking_request_code,
            doc_entry=pr.doc_entry,
            order_items=order_items,
        )
    except Exception as e:
        raise OuterServicesError(f"WMS request failed: {e}")

    logger.info(f"WMS response: {resp}")
    if not resp.get("success"):
        raise OuterServicesError(f"WMS rejected pickup: | {resp.get('error', 'unknown error')} | {resp.get('message', 'unknown message')}")

    pickup_id = (resp.get("data") or {}).get("pickup_id")
    pr.wms_reference = str(pickup_id) if pickup_id is not None else None


def create_for_sales_order(doc_entry, data):
    """
    Create a picking request for a SalesOrder.
    Each item in the payload may specify sales_item_id or material_list_id.
    """
    try:
        so = sales_order_repository.get_sales_order_by_doc_entry(doc_entry)
        if not so:
            raise NotFoundError(f"Sales Order {doc_entry} not found")

        from app.services import sales_order_service
        sales_order_service.assert_so_not_canceling(doc_entry)

        items = _build_items(data.get("items", []))

        pr = PickingRequest(
            picking_request_code=document_code_service.generate_number("PR"),
            doc_entry=doc_entry,
            status=PickingRequestStatus.PENDING,
            remark=data.get("remark"),
        )
        picking_request_repository.create_picking_request(pr)
        db.session.flush()

        for item in items:
            item.picking_request_id = pr.picking_request_id
            db.session.add(item)

        _call_wms_create_pickup(pr, items)
        # raise ManualRaiseToTest("Let's see what it does...")
        db.session.commit()

        return picking_request_repository.get_picking_request_detail_by_id(pr.picking_request_id)
    except Exception:
        db.session.rollback()
        raise


def update_status(picking_request_id, data):
    """
    Manually update the status of a picking request.
    Allowed transitions: PENDING → SENT → SUCCESS | FAILED
    """
    try:
        pr = picking_request_repository.get_picking_request_detail_by_id(picking_request_id)
        if not pr:
            raise NotFoundError(f"Picking Request {picking_request_id} not found")

        raw_status = data.get("status", "").strip().upper()
        try:
            new_status = PickingRequestStatus[raw_status]
        except KeyError:
            allowed = [s.value for s in PickingRequestStatus]
            raise ValidationError(f"status ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")

        valid_transitions = {
            PickingRequestStatus.PENDING: {PickingRequestStatus.SENT, PickingRequestStatus.FAILED},
            PickingRequestStatus.SENT:    {PickingRequestStatus.SUCCESS, PickingRequestStatus.FAILED},
            PickingRequestStatus.SUCCESS: set(),
            PickingRequestStatus.FAILED:  {PickingRequestStatus.PENDING},
        }
        if new_status not in valid_transitions[pr.status]:
            raise ValidationError(
                f"ไม่สามารถเปลี่ยนสถานะจาก {pr.status.value} เป็น {new_status.value} ได้"
            )

        pr.status = new_status
        if data.get("wms_reference"):
            pr.wms_reference = data["wms_reference"]
        if data.get("remark") is not None:
            pr.remark = data["remark"]

        db.session.commit()
        return pr
    except Exception:
        db.session.rollback()
        raise


def get_list(data):
    page = data.get("page", 1)
    per_page = data.get("per_page", 10)
    search = data.get("search", "")

    raw_status = data.get("status", "").strip().upper()
    status = None
    if raw_status:
        try:
            status = PickingRequestStatus[raw_status]
        except KeyError:
            allowed = [s.value for s in PickingRequestStatus]
            raise ValidationError(f"status ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")

    doc_entry = data.get("doc_entry")

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    start_date = convert_start_date(start_date) if start_date else None
    end_date = convert_end_date(end_date) if end_date else None

    return picking_request_repository.get_picking_request_list(
        page=page,
        per_page=per_page,
        search=search,
        status=status,
        doc_entry=doc_entry,
        start_date=start_date,
        end_date=end_date,
    )


def get_detail(picking_request_id):
    pr = picking_request_repository.get_picking_request_full_detail_by_id(picking_request_id)
    if not pr:
        raise NotFoundError(f"Picking Request {picking_request_id} not found")
    return pr


def get_by_sales_order(doc_entry):
    so = sales_order_repository.get_sales_order_by_doc_entry(doc_entry)
    if not so:
        raise NotFoundError(f"Sales Order {doc_entry} not found")
    return picking_request_repository.get_picking_requests_by_doc_entry(doc_entry)

def get_by_wms_reference(wms_reference):
    try:
        pr = picking_request_repository.get_by_wms_reference_repo(wms_reference)
        return pr
    except Exception:
        raise

def get_by_code(picking_request_code):
    try:
        pr = picking_request_repository.get_by_code_repo(picking_request_code)
        return pr
    except Exception:
        raise
