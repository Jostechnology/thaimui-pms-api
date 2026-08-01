from flask import g
from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import (
    ComponentEditRequest,
    ComponentEditRequestStatus,
    ItemComponent,
    WorkOrder,
)


def create_edit_request(edit_request):
    try:
        db.session.add(edit_request)
        return edit_request
    except Exception:
        raise


def get_edit_request_by_id(edit_request_id):
    try:
        query = db.session.query(ComponentEditRequest).filter(
            ComponentEditRequest.edit_request_id == edit_request_id
        )
        return query.first()
    except Exception:
        raise


def get_edit_request_detail(edit_request_id):
    try:
        query = db.session.query(ComponentEditRequest).options(
            selectinload(ComponentEditRequest.item_component),
            selectinload(ComponentEditRequest.work_order),
            selectinload(ComponentEditRequest.consumed_version),
        ).filter(ComponentEditRequest.edit_request_id == edit_request_id)
        return query.first()
    except Exception:
        raise


def get_all_edit_requests(page, per_page, search=None, status=None, work_order_id=None):
    try:
        # Branch comes off the WorkOrder, not off ComponentEditRequest.branch_id:
        # ItemComponent.branch_id is nullable and frequently unset, so the
        # denormalised column cannot be trusted to scope the inbox.
        query = (
            db.session.query(ComponentEditRequest)
            .join(WorkOrder, WorkOrder.work_order_id == ComponentEditRequest.work_order_id)
            .join(ItemComponent, ItemComponent.item_component_id == ComponentEditRequest.item_component_id)
            .options(
                selectinload(ComponentEditRequest.item_component),
                selectinload(ComponentEditRequest.work_order),
            )
        )

        branch_id = g.get("branch_id")
        if branch_id:
            query = query.filter(WorkOrder.branch_id == branch_id)

        if status:
            query = query.filter(ComponentEditRequest.status == status)
        if work_order_id:
            query = query.filter(ComponentEditRequest.work_order_id == work_order_id)
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    ItemComponent.component_name.like(like),
                    WorkOrder.work_order_code.like(like),
                    ComponentEditRequest.reason.like(like),
                    ComponentEditRequest.created_by.like(like),
                )
            )

        query = query.order_by(ComponentEditRequest.created_date.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
    except Exception:
        raise


def get_approved_unconsumed(item_component_id):
    """The single-use unlock. Oldest first so a queue of approvals is consumed in order."""
    try:
        query = db.session.query(ComponentEditRequest).filter(
            ComponentEditRequest.item_component_id == item_component_id,
            ComponentEditRequest.status == ComponentEditRequestStatus.APPROVED,
        ).order_by(ComponentEditRequest.reviewed_date.asc(), ComponentEditRequest.edit_request_id.asc())
        return query.first()
    except Exception:
        raise


def get_open_request_for_component(item_component_id):
    """A PENDING or APPROVED request already exists — block filing a duplicate."""
    try:
        query = db.session.query(ComponentEditRequest).filter(
            ComponentEditRequest.item_component_id == item_component_id,
            ComponentEditRequest.status.in_(
                [ComponentEditRequestStatus.PENDING, ComponentEditRequestStatus.APPROVED]
            ),
        ).order_by(ComponentEditRequest.edit_request_id.asc())
        return query.first()
    except Exception:
        raise


def get_requests_by_item_component(item_component_id):
    try:
        query = db.session.query(ComponentEditRequest).filter(
            ComponentEditRequest.item_component_id == item_component_id
        ).order_by(ComponentEditRequest.created_date.desc())
        return query.all()
    except Exception:
        raise
