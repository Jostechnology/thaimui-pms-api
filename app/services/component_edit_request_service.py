from flask import g

from app.app import db
from app.con_sqlalchemy import ComponentEditRequest, ComponentEditRequestStatus
from app.exception import (
    AuthorizationError,
    NotFoundError,
    UniqueError,
    ValidationError,
)
from app.repositories import (
    component_edit_request_repository,
    item_component_repository,
    work_order_repository,
)
from app.services import item_component_service
from app.con_sqlalchemy import bangkok_now


def _parse_status(status):
    if not status:
        return None
    try:
        return ComponentEditRequestStatus(status)
    except ValueError:
        raise ValidationError(f"สถานะไม่ถูกต้อง: {status}")


def get_all_edit_requests(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        status = _parse_status(data.get("status"))
        work_order_id = data.get("work_order_id")

        result = component_edit_request_repository.get_all_edit_requests(
            page, per_page, search, status, work_order_id
        )
        return {
            "items": result.items,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
        }
    except Exception:
        raise


def get_edit_request_by_id(edit_request_id):
    try:
        edit_request = component_edit_request_repository.get_edit_request_by_id(edit_request_id)
        if not edit_request:
            raise NotFoundError(f"ไม่พบคำขอแก้ไขเอกสาร {edit_request_id}")
        return edit_request
    except Exception:
        raise


def get_edit_request_detail(edit_request_id):
    try:
        edit_request = component_edit_request_repository.get_edit_request_detail(edit_request_id)
        if not edit_request:
            raise NotFoundError(f"ไม่พบคำขอแก้ไขเอกสาร {edit_request_id}")
        return edit_request
    except Exception:
        raise


def get_requests_for_component(item_component_id):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return component_edit_request_repository.get_requests_by_item_component(item_component_id)
    except Exception:
        raise


def create_edit_request(item_component_id, data):
    """Sales asks Production to unlock a component whose WorkOrder is in production."""
    try:
        reason = (data.get("reason") or "").strip()
        if not reason:
            raise ValidationError("กรุณาระบุเหตุผลในการขอแก้ไข")

        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        if not item_component_service.is_component_locked(item):
            raise ValidationError(
                "ใบสั่งผลิตนี้ยังไม่เริ่มการผลิต สามารถแก้ไขเอกสารได้โดยไม่ต้องขออนุมัติ"
            )

        open_request = component_edit_request_repository.get_open_request_for_component(
            item_component_id
        )
        if open_request:
            raise UniqueError(
                f"มีคำขอแก้ไขที่ยังไม่ปิด (#{open_request.edit_request_id}) "
                f"สำหรับส่วนประกอบนี้อยู่แล้ว"
            )

        # ItemComponent.branch_id is nullable and often unset; the WorkOrder
        # always carries the branch it was created under.
        work_order = work_order_repository.get_work_order_light(item.work_order_id)
        branch_id = item.branch_id or (work_order.branch_id if work_order else None)

        edit_request = ComponentEditRequest(
            item_component_id=item_component_id,
            work_order_id=item.work_order_id,
            base_version_no=item.doc_version,
            reason=reason,
            status=ComponentEditRequestStatus.PENDING,
            branch_id=branch_id,
        )
        component_edit_request_repository.create_edit_request(edit_request)
        db.session.commit()
        return edit_request
    except Exception:
        db.session.rollback()
        raise


def _review(edit_request_id, new_status, remark):
    edit_request = component_edit_request_repository.get_edit_request_by_id(edit_request_id)
    if not edit_request:
        raise NotFoundError(f"ไม่พบคำขอแก้ไขเอกสาร {edit_request_id}")
    if edit_request.status != ComponentEditRequestStatus.PENDING:
        raise ValidationError(
            f"คำขอนี้ถูกดำเนินการไปแล้ว (สถานะ: {edit_request.status.value})"
        )

    reviewer = g.get("username")
    # Four-eyes: the person who asked for the edit cannot sign it off.
    if reviewer and edit_request.created_by and reviewer == edit_request.created_by:
        raise AuthorizationError("ผู้ขอแก้ไขไม่สามารถอนุมัติคำขอของตนเองได้")

    edit_request.status = new_status
    edit_request.reviewed_by = reviewer
    edit_request.reviewed_date = bangkok_now()
    edit_request.review_remark = remark
    db.session.commit()
    return edit_request


def approve_edit_request(edit_request_id, data):
    """Approval is a single-use key — the next save on that component consumes it."""
    try:
        return _review(
            edit_request_id,
            ComponentEditRequestStatus.APPROVED,
            (data or {}).get("review_remark"),
        )
    except Exception:
        db.session.rollback()
        raise


def reject_edit_request(edit_request_id, data):
    try:
        remark = ((data or {}).get("review_remark") or "").strip()
        if not remark:
            raise ValidationError("กรุณาระบุเหตุผลในการปฏิเสธคำขอ")
        return _review(edit_request_id, ComponentEditRequestStatus.REJECTED, remark)
    except Exception:
        db.session.rollback()
        raise


def cancel_edit_request(edit_request_id):
    """Requester withdraws their own PENDING request."""
    try:
        edit_request = component_edit_request_repository.get_edit_request_by_id(edit_request_id)
        if not edit_request:
            raise NotFoundError(f"ไม่พบคำขอแก้ไขเอกสาร {edit_request_id}")
        if edit_request.status != ComponentEditRequestStatus.PENDING:
            raise ValidationError(
                f"ยกเลิกได้เฉพาะคำขอที่รออนุมัติ (สถานะปัจจุบัน: {edit_request.status.value})"
            )

        username = g.get("username")
        if username and edit_request.created_by and username != edit_request.created_by:
            raise AuthorizationError("ยกเลิกได้เฉพาะคำขอที่ตนเองเป็นผู้สร้าง")

        edit_request.status = ComponentEditRequestStatus.CANCELLED
        db.session.commit()
        return edit_request
    except Exception:
        db.session.rollback()
        raise
