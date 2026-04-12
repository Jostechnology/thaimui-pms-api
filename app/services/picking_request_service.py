from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem,
    PickingRequestStatus,
)
from app.repositories import picking_request_repository, sales_order_repository
from app.services import document_code_service
from app.app import db
from app.exception import NotFoundError, ValidationError, OuterServicesError


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


def _call_wms_create_pickup(pr, items):
    """
    Call WMS create_pickup_from_pms if the service is configured.
    On success: set pr.status = SENT, pr.wms_reference = pickup_id.
    On failure (success=False or exception): raise OuterServicesError.
    """
    from app.extensions import wms_service
    if wms_service is None:
        return

    order_items = [
        {
            "order_line_num": item.order_line_num,
            "quantity": item.quantity,
        }
        for item in items
        if item.order_line_num is not None
    ]

    if not order_items:
        return

    try:
        resp = wms_service.create_pickup_from_pms(
            doc_entry=pr.doc_entry,
            order_items=order_items,
        )
    except Exception as e:
        raise OuterServicesError(f"WMS request failed: {e}")

    if not resp.get("success"):
        raise OuterServicesError(f"WMS rejected pickup: {resp.get('message', 'unknown error')}")

    pickup_id = (resp.get("data") or {}).get("pickup_id")
    pr.wms_reference = str(pickup_id) if pickup_id is not None else None
    pr.status = PickingRequestStatus.SENT


def create_for_sales_order(doc_entry, data):
    """
    Create a picking request for a SalesOrder.
    Each item in the payload may specify sales_item_id or material_list_id.
    """
    try:
        so = sales_order_repository.get_sales_order_by_doc_entry(doc_entry)
        if not so:
            raise NotFoundError(f"Sales Order {doc_entry} not found")

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

    return picking_request_repository.get_picking_request_list(
        page=page,
        per_page=per_page,
        search=search,
        status=status,
        doc_entry=doc_entry,
    )


def get_by_sales_order(doc_entry):
    so = sales_order_repository.get_sales_order_by_doc_entry(doc_entry)
    if not so:
        raise NotFoundError(f"Sales Order {doc_entry} not found")
    return picking_request_repository.get_picking_requests_by_doc_entry(doc_entry)
