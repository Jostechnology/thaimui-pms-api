from app.con_sqlalchemy import PickingRequest, PickingRequestItem, PickingRequestStatus, SalesOrder
from app.app import db
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import joinedload, selectinload, contains_eager

from app.exception import NotFoundError


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


def get_picking_request_full_detail_by_id(picking_request_id):
    """Full detail: sales_order + items."""
    query = db.session.query(PickingRequest).options(
        joinedload(PickingRequest.sales_order),
        selectinload(PickingRequest.items),
    ).filter(PickingRequest.picking_request_id == picking_request_id)
    return query.first()


def get_picking_requests_by_doc_entry(doc_entry):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items)
    ).filter(PickingRequest.doc_entry == doc_entry)
    return query.all()


def get_picking_request_item_by_id(picking_request_item_id):
    query = db.session.query(PickingRequestItem).filter(
        PickingRequestItem.picking_request_item_id == picking_request_item_id
    )
    return query.first()


def has_success_picking_request(doc_entry):
    """True if at least one SUCCESS PickingRequest exists for the SalesOrder."""
    query = db.session.query(PickingRequest.picking_request_id).filter(
        PickingRequest.doc_entry == doc_entry,
        PickingRequest.status == PickingRequestStatus.SUCCESS,
    )
    return query.first() is not None


def get_picking_request_list(page, per_page, search="", status=None, doc_entry=None, start_date=None, end_date=None):
    query = (
        db.session.query(PickingRequest)
        .outerjoin(SalesOrder, SalesOrder.doc_entry == PickingRequest.doc_entry)
        .options(
            selectinload(PickingRequest.items),
            contains_eager(PickingRequest.sales_order),
        )
    )

    if search:
        query = query.filter(
            or_(
                PickingRequest.picking_request_code.ilike(f"%{search}%"),
                PickingRequest.wms_reference.ilike(f"%{search}%"),
                PickingRequest.created_by.ilike(f"%{search}%"),
                cast(SalesOrder.doc_num, String).ilike(f"%{search}%"),
            )
        )

    if status:
        query = query.filter(PickingRequest.status == status)

    if doc_entry:
        query = query.filter(PickingRequest.doc_entry == doc_entry)

    if start_date is not None:
        query = query.filter(PickingRequest.created_date >= start_date)
    if end_date is not None:
        query = query.filter(PickingRequest.created_date <= end_date)

    result = query.order_by(PickingRequest.picking_request_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}

def get_by_wms_reference_repo(wms_reference):
    pr = db.session.query(PickingRequest).filter(PickingRequest.wms_reference == wms_reference).first()
    if pr is None:
        raise NotFoundError(f"ไม่พบ Picking Request WMS_Reference : {wms_reference}")

    return pr


def get_by_code_repo(picking_request_code):
    pr = db.session.query(PickingRequest).filter(PickingRequest.picking_request_code == picking_request_code).first()
    if pr is None:
        raise NotFoundError(f"ไม่พบ Picking Request Code : {picking_request_code}")

    return pr
