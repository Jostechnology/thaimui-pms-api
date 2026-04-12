from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem,
    PickingRequestStatus, PickingRequestType,
    TestSessionStatus,
)
from app.repositories import picking_request_repository, work_run_repository, test_result_repository
from app.services import document_code_service
from app.app import db
from app.exception import NotFoundError, ValidationError, OuterServicesError


def _build_items(items_data, default_unit=None):
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
            unit=item.get("unit") or default_unit,
            remark=item.get("remark"),
        ))
    return result


def _call_wms_create_pickup(pr, sales_item, items, purpose: str):
    """
    Call WMS create_pickup_from_pms if the service is configured.
    On success: set pr.status = SENT, pr.wms_reference = pickup_id.
    On failure (success=False or exception): raise OuterServicesError.
    """
    from app.extensions import wms_service
    if wms_service is None or sales_item is None:
        return

    order_items = [
        {
            "order_line_num": sales_item.order_line_num,
            "quantity": item.quantity,
            "purpose": purpose,
        }
        for item in items
    ]

    try:
        resp = wms_service.create_pickup_from_pms(
            doc_entry=sales_item.doc_entry,
            order_items=order_items,
        )
    except Exception as e:
        raise OuterServicesError(f"WMS request failed: {e}")

    if not resp.get("success"):
        raise OuterServicesError(f"WMS rejected pickup: {resp.get('message', 'unknown error')}")

    pickup_id = (resp.get("data") or {}).get("pickup_id")
    pr.wms_reference = str(pickup_id) if pickup_id is not None else None
    pr.status = PickingRequestStatus.SENT


def create_for_work_run(work_run_id, data):
    """
    Create a picking request linked to a WorkRun.
    No quantity validation — users may re-request material freely.
    """
    try:
        work_run = work_run_repository.get_work_run_by_id(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")

        sales_item = work_run_repository.get_sales_item_by_work_run(work_run_id)
        default_unit = sales_item.unit_name if sales_item else None

        items = _build_items(data.get("items", []), default_unit=default_unit)

        pr = PickingRequest(
            request_type=PickingRequestType.WORK_RUN,
            picking_request_code=document_code_service.generate_number("PR"),
            work_run_id=work_run_id,
            status=PickingRequestStatus.PENDING,
            remark=data.get("remark"),
        )
        picking_request_repository.create_picking_request(pr)
        db.session.flush()

        for item in items:
            item.picking_request_id = pr.picking_request_id
            db.session.add(item)

        _call_wms_create_pickup(pr, sales_item, items, purpose="PROD")

        db.session.commit()

        return picking_request_repository.get_picking_request_detail_by_id(pr.picking_request_id)
    except Exception:
        db.session.rollback()
        raise


def create_for_test_result(test_result_id, data):
    """
    Create a picking request linked to a TestResult.
    Only allowed while the test session is INPROGRESS (Phase 1).
    """
    try:
        test_result = test_result_repository.get_test_result_by_id(test_result_id)
        if not test_result:
            raise NotFoundError(f"Test Result {test_result_id} not found")
        if test_result.session_status != TestSessionStatus.INPROGRESS:
            raise ValidationError("สามารถส่ง picking request ได้เฉพาะเมื่อ test session อยู่ในสถานะ INPROGRESS เท่านั้น")

        sales_item = test_result_repository.get_sales_item_by_test_result(test_result_id)
        default_unit = sales_item.unit_name if sales_item else None

        items = _build_items(data.get("items", []), default_unit=default_unit)

        pr = PickingRequest(
            request_type=PickingRequestType.TEST_RESULT,
            picking_request_code=document_code_service.generate_number("PR"),
            test_result_id=test_result_id,
            status=PickingRequestStatus.PENDING,
            remark=data.get("remark"),
        )
        picking_request_repository.create_picking_request(pr)
        db.session.flush()

        for item in items:
            item.picking_request_id = pr.picking_request_id
            db.session.add(item)

        _call_wms_create_pickup(pr, sales_item, items, purpose="TEST")

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

    raw_type = data.get("request_type", "").strip().upper()
    request_type = None
    if raw_type:
        try:
            request_type = PickingRequestType[raw_type]
        except KeyError:
            allowed = [t.value for t in PickingRequestType]
            raise ValidationError(f"request_type ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")

    return picking_request_repository.get_picking_request_list(
        page=page,
        per_page=per_page,
        search=search,
        status=status,
        request_type=request_type,
    )


def get_by_work_run(work_run_id):
    work_run = work_run_repository.get_work_run_by_id(work_run_id)
    if not work_run:
        raise NotFoundError(f"Work Run {work_run_id} not found")
    return picking_request_repository.get_picking_requests_by_work_run(work_run_id)


def get_by_test_result(test_result_id):
    test_result = test_result_repository.get_test_result_by_id(test_result_id)
    if not test_result:
        raise NotFoundError(f"Test Result {test_result_id} not found")
    return picking_request_repository.get_picking_requests_by_test_result(test_result_id)
