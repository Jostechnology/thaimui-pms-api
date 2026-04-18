from app.con_sqlalchemy import PickingRequest, PickingRequestItem, PickingRequestStatus, TestResultPickingItem, WorkRunPickingItem, PickingItemAdjustment, TestResult, WorkRun
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

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
    """Full detail: items + each item's test_result/work_run consumptions + adjustments."""
    query = db.session.query(PickingRequest).options(
        joinedload(PickingRequest.sales_order),
        selectinload(PickingRequest.items).selectinload(PickingRequestItem.test_result_consumptions).selectinload(TestResultPickingItem.test_result),
        selectinload(PickingRequest.items).selectinload(PickingRequestItem.work_run_consumptions).selectinload(WorkRunPickingItem.work_run),
        selectinload(PickingRequest.items).selectinload(PickingRequestItem.adjustments),
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


def get_available_picking_items_for_material(material_list_id):
    """PickingRequestItems where material_list_id matches and parent PR is SUCCESS, ordered FIFO."""
    query = (
        db.session.query(PickingRequestItem)
        .join(PickingRequest, PickingRequest.picking_request_id == PickingRequestItem.picking_request_id)
        .filter(
            PickingRequestItem.material_list_id == material_list_id,
            PickingRequest.status == PickingRequestStatus.SUCCESS,
        )
        .order_by(PickingRequestItem.picking_request_item_id.asc())
    )
    return query.all()


def get_total_committed_qty(picking_request_item_id):
    """
    Total committed qty from a PickingRequestItem across ALL consumers.
    Active rows (qty_consumed IS NULL) count full qty_allocated.
    Finished rows count actual qty_consumed (releases leftover to pool).
    """
    from sqlalchemy import func, case

    trpi_sum = db.session.query(
        func.coalesce(
            func.sum(
                case(
                    (TestResultPickingItem.qty_consumed.isnot(None), TestResultPickingItem.qty_consumed),
                    else_=TestResultPickingItem.qty_allocated,
                )
            ), 0
        )
    ).filter(
        TestResultPickingItem.picking_request_item_id == picking_request_item_id
    ).scalar()

    wrpi_sum = db.session.query(
        func.coalesce(
            func.sum(
                case(
                    (WorkRunPickingItem.qty_consumed.isnot(None), WorkRunPickingItem.qty_consumed),
                    else_=WorkRunPickingItem.qty_allocated,
                )
            ), 0
        )
    ).filter(
        WorkRunPickingItem.picking_request_item_id == picking_request_item_id
    ).scalar()

    adj_sum = db.session.query(
        func.coalesce(func.sum(PickingItemAdjustment.delta_qty), 0)
    ).filter(
        PickingItemAdjustment.picking_request_item_id == picking_request_item_id
    ).scalar()

    # adjustments reduce/increase the available pool, not committed qty directly
    # net_committed = committed - adjustments (negative adj shrinks pool = same as more committed)
    return trpi_sum + wrpi_sum - adj_sum


def get_non_failed_picked_qty_for_sales_item(sales_item_id):
    """Sum of quantities across all non-FAILED PR items for a sales_item."""
    query = (
        db.session.query(
            db.func.coalesce(db.func.sum(PickingRequestItem.quantity), 0)
        )
        .join(PickingRequest, PickingRequest.picking_request_id == PickingRequestItem.picking_request_id)
        .filter(
            PickingRequestItem.sales_item_id == sales_item_id,
            PickingRequest.status != PickingRequestStatus.FAILED,
        )
    )
    return query.scalar()


def create_picking_item_adjustment(adjustment):
    db.session.add(adjustment)
    return adjustment


def get_picking_item_adjustment_by_id(adjustment_id):
    query = db.session.query(PickingItemAdjustment).filter(
        PickingItemAdjustment.id == adjustment_id
    )
    return query.first()


def get_picking_item_adjustments_by_item(picking_request_item_id, page, per_page):
    query = db.session.query(PickingItemAdjustment).filter(
        PickingItemAdjustment.picking_request_item_id == picking_request_item_id
    ).order_by(PickingItemAdjustment.id.desc())
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}


def get_picking_item_adjustments_by_picking_request(picking_request_id, page, per_page):
    query = (
        db.session.query(PickingItemAdjustment)
        .join(PickingRequestItem, PickingRequestItem.picking_request_item_id == PickingItemAdjustment.picking_request_item_id)
        .filter(PickingRequestItem.picking_request_id == picking_request_id)
        .order_by(PickingItemAdjustment.id.desc())
    )
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}


def get_picking_request_list(page, per_page, search="", status=None, doc_entry=None):
    query = db.session.query(PickingRequest).options(
        selectinload(PickingRequest.items),
        joinedload(PickingRequest.sales_order)
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
