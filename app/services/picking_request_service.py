from app.con_sqlalchemy import (
    PickingRequest, PickingRequestItem,
    PickingRequestStatus, PickingRequestType,
    TestSessionStatus,
)
from app.repositories import picking_request_repository, work_run_repository, test_result_repository
from app.services import document_code_service
from app.app import db
from app.exception import NotFoundError, ValidationError
from app.messaging import EXCHANGE_PICKING, RK_PICKING_REQUESTED, RK_PICKING_RECEIVED
from app.messaging.publisher import publish_safely

def _build_wms_payload(pr, items):
    return {
        "picking_request_id": pr.picking_request_id,
        "picking_request_code": pr.picking_request_code,
        "source_type": pr.request_type.value,
        "work_run_id": pr.work_run_id,
        "test_result_id": pr.test_result_id,
        "remark": pr.remark,
        "items": [
            {"item_code": i.item_code, "item_name": i.item_name,
             "quantity": i.quantity, "unit": i.unit, "remark": i.remark}
            for i in items
        ],
    }


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
        ))
    return result


def create_for_work_run(work_run_id, data):
    """
    Create a picking request linked to a WorkRun.
    No quantity validation — users may re-request material freely.
    """
    try:
        work_run = work_run_repository.get_work_run_by_id(work_run_id)
        if not work_run:
            raise NotFoundError(f"Work Run {work_run_id} not found")

        items = _build_items(data.get("items", []))

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

        db.session.commit()

        publish_safely(EXCHANGE_PICKING, RK_PICKING_REQUESTED, _build_wms_payload(pr, items))
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

        items = _build_items(data.get("items", []))

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

        db.session.commit()

        publish_safely(EXCHANGE_PICKING, RK_PICKING_REQUESTED, _build_wms_payload(pr, items))
        return picking_request_repository.get_picking_request_detail_by_id(pr.picking_request_id)
    except Exception:
        db.session.rollback()
        raise


def _transition(pr, new_status, allowed_from):
    """Idempotent state transition. No-op if already in new_status; error on illegal jumps."""
    if pr.status == new_status:
        return False
    if pr.status not in allowed_from:
        raise ValidationError(
            f"Cannot transition picking request from {pr.status.value} to {new_status.value}"
        )
    pr.status = new_status
    return True


def mark_picking(picking_request_id, payload):
    """Consumer handler: WMS is picking."""
    pr = picking_request_repository.get_picking_request_by_id(picking_request_id)
    if not pr:
        raise NotFoundError(f"Picking Request {picking_request_id} not found")
    if _transition(pr, PickingRequestStatus.PICKING, {PickingRequestStatus.PENDING}):
        if payload.get("wms_reference"):
            pr.wms_reference = payload["wms_reference"]
    return pr


def mark_sent(picking_request_id, payload):
    """Consumer handler: WMS dispatched."""
    pr = picking_request_repository.get_picking_request_by_id(picking_request_id)
    if not pr:
        raise NotFoundError(f"Picking Request {picking_request_id} not found")
    _transition(
        pr, PickingRequestStatus.SENT,
        {PickingRequestStatus.PENDING, PickingRequestStatus.PICKING},
    )
    if payload.get("wms_reference"):
        pr.wms_reference = payload["wms_reference"]
    return pr


def mark_received(picking_request_id):
    """Called from our UI when the user clicks Receive."""
    try:
        pr = picking_request_repository.get_picking_request_by_id(picking_request_id)
        if not pr:
            raise NotFoundError(f"Picking Request {picking_request_id} not found")
        changed = _transition(
            pr, PickingRequestStatus.RECEIVED,
            {PickingRequestStatus.SENT, PickingRequestStatus.PICKING},
        )
        db.session.commit()
        if changed:
            publish_safely(EXCHANGE_PICKING, RK_PICKING_RECEIVED, {
                "picking_request_id": pr.picking_request_id,
                "picking_request_code": pr.picking_request_code,
                "wms_reference": pr.wms_reference,
            })
        return picking_request_repository.get_picking_request_detail_by_id(picking_request_id)
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
