from app.con_sqlalchemy import PickingRequest, PickingRequestItem, PickingRequestStatus, PickingRequestType, WorkRun, TestResult
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


def get_picking_requests_by_work_run(work_run_id):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items)
    ).filter(PickingRequest.work_run_id == work_run_id)
    return query.all()


def get_picking_requests_by_test_result(test_result_id):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items)
    ).filter(PickingRequest.test_result_id == test_result_id)
    return query.all()


def has_unsolved_picking_requests_for_work_run(work_run_id):
    query = db.session.query(PickingRequest).filter(
        PickingRequest.work_run_id == work_run_id,
        PickingRequest.status.in_([PickingRequestStatus.PENDING, PickingRequestStatus.SENT])
    )
    return query.first() is not None


def has_unsolved_picking_requests_for_test_result(test_result_id):
    query = db.session.query(PickingRequest).filter(
        PickingRequest.test_result_id == test_result_id,
        PickingRequest.status.in_([PickingRequestStatus.PENDING, PickingRequestStatus.SENT])
    )
    return query.first() is not None


def get_picking_request_list(page, per_page, search="", status=None, request_type=None):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items),
        selectinload(PickingRequest.work_run),
        selectinload(PickingRequest.test_result),
    )

    if search:
        query = query.filter(
            or_(
                PickingRequest.wms_reference.ilike(f"%{search}%"),
                PickingRequest.created_by.ilike(f"%{search}%"),
            )
        )

    if status:
        query = query.filter(PickingRequest.status == status)

    if request_type:
        query = query.filter(PickingRequest.request_type == request_type)

    result = query.order_by(PickingRequest.picking_request_id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
