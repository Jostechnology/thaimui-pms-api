from app.con_sqlalchemy import PickingRequest, PickingRequestItem, PickingRequestStatus
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import selectinload


def create_picking_request(picking_request):
    db.session.add(picking_request)
    return picking_request


def get_picking_request_by_id(picking_request_id):
    query = db.session.query(PickingRequest).filter(
        PickingRequest.picking_request_id == picking_request_id
    )
    return query.first()


def get_picking_request_detail_by_id(picking_request_id):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items)
    ).filter(PickingRequest.picking_request_id == picking_request_id)
    return query.first()


def get_picking_requests_by_doc_entry(doc_entry):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items)
    ).filter(PickingRequest.doc_entry == doc_entry)
    return query.all()


def get_available_picking_items_for_sales_item(sales_item_id):
    """PickingRequestItems where sales_item_id matches and parent PR is SUCCESS, ordered FIFO."""
    query = (
        db.session.query(PickingRequestItem)
        .join(PickingRequest, PickingRequest.picking_request_id == PickingRequestItem.picking_request_id)
        .filter(
            PickingRequestItem.sales_item_id == sales_item_id,
            PickingRequest.status == PickingRequestStatus.SUCCESS,
        )
        .order_by(PickingRequestItem.picking_request_item_id.asc())
    )
    return query.all()


def get_picking_request_list(page, per_page, search="", status=None, doc_entry=None):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items),
    )

    if search:
        query = query.filter(
            or_(
                PickingRequest.picking_request_code.ilike(f"%{search}%"),
                PickingRequest.wms_reference.ilike(f"%{search}%"),
                PickingRequest.created_by.ilike(f"%{search}%"),
            )
        )

    if status:
        query = query.filter(PickingRequest.status == status)

    if doc_entry:
        query = query.filter(PickingRequest.doc_entry == doc_entry)

    result = query.order_by(PickingRequest.picking_request_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
