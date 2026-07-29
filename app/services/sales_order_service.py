from app.exception import MissingFieldsError, OuterServicesError, ValidationError
from app.repositories import material_repository, sales_item_repository, sales_order_repository
from app.extensions import center_service
from app.app import db
from app.services import branch_service, cache_service, work_order_service, transaction_service
from app.con_sqlalchemy import SalesOrder, SalesItem, MaterialList, SalesItemStatus, SalesOrderStatus, UrgencyLevel, WorkOrderStatus, MANUFACTURED_ITEM_GROUP
from app.extensions import wms_service
from app.utils import convert_start_date, convert_end_date


def _parse_urgency(raw, default=None):
    """Coerce raw urgency string to UrgencyLevel enum; raise ValidationError if invalid."""
    if raw is None or raw == "":
        return default
    try:
        return UrgencyLevel[str(raw).strip().upper()]
    except KeyError:
        allowed = [u.value for u in UrgencyLevel]
        raise ValidationError(f"urgency_level ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")

def search_sales_order(data, branch_id=None):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = sales_order_repository.search_sales_order(page, per_page, search, branch_id=branch_id)
        # cache_service()
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def assign_branch_to_sales_order(doc_entry, branch_id):
    try:
        sales_order, old_branch_id = sales_order_repository.assign_branch(doc_entry, branch_id)
        db.session.commit()
        return sales_order, old_branch_id
    except Exception:
        db.session.rollback()
        raise


def get_all_sales_orders(data, branch_id=None):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_date = convert_start_date(start_date) if start_date else None
        end_date = convert_end_date(end_date) if end_date else None
        urgency_level = _parse_urgency(data.get("urgency_level"))
        sort_by = data.get("sort_by") or None
        sort_order = (data.get("sort_order") or "desc").lower()
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"
        result = sales_order_repository.get_all_sales_orders(
            page, per_page, search,
            branch_id=branch_id,
            start_date=start_date,
            end_date=end_date,
            urgency_level=urgency_level,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items_data = []
        for row in result.items:
            so = row.SalesOrder
            branch = row.Branch if row.Branch else None
            items_data.append({
                "doc_entry": so.doc_entry,
                "doc_num": so.doc_num,
                "card_code": so.card_code,
                "card_name": so.card_name,
                "slp_code": so.slp_code,
                "slp_name": so.slp_name,
                "bpl_code": so.bpl_code,
                "bpl_name": so.bpl_name,
                "group_code": so.group_code,
                "group_name": so.group_name,
                "created_date": so.created_date.strftime("%Y-%m-%d %H:%M:%S") if so.created_date else None,
                "items_total": row.items_total,
                "quantity_to_produce": row.quantity_to_produce,
                "produced_qty": row.produced_qty,
                "qc_count": row.qc_count,
                "qc_passed": row.qc_passed,
                "qc_failed": row.qc_failed,
                "produce_total": row.produce_total,
                "produce_has_workorder": row.produce_has_workorder,
                "test_total": row.test_total,
                "test_has_qcworkorder": row.test_has_qcworkorder,
                "status" : so.status.name,
                "urgency_level" : so.urgency_level.name if so.urgency_level else None,
                "branch_code" : branch.branch_code if branch else None,
                "branch_name" : branch.branch_name if branch else None
            })

        return {
            "items": items_data,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
        }
    except Exception:
        raise

def get_sales_items_from_sales_order(doc_entry):
    try:
        return sales_item_repository.get_sales_items_by_doc_entry(doc_entry)
    except Exception:
        raise

def get_material_list_from_sales_order(doc_entry):
    try:
        return material_repository.get_material_list_from_doc_entry(doc_entry)
    except Exception:
        raise


def get_sales_items_and_material_lists(doc_entry):
    try:
        sales_items = sales_item_repository.get_sales_items_by_doc_entry(doc_entry)
        material_lists = material_repository.get_material_list_from_doc_entry(doc_entry)
        return {"sales_items": sales_items, "material_lists": material_lists}
    except Exception:
        raise


def get_sales_order_detail(doc_entry, branch_id=None):
    try:
        result, branch = sales_order_repository.get_sales_order_detail(doc_entry, branch_id=branch_id)
        items = result.sales_items
        
        materials = []
        for i in items:
            materials.extend(i.material_list)
        return result, items, materials, branch
    except Exception:
        db.session.rollback()
        raise

def get_test_sales_order():
    try:
        response = center_service.request(
            method="POST",
            endpoint="/api/ORDR/get_test_quick",
        )
        data = response["json"]
        print(data)
        finished = []
        for so in data:
            sales_order, no_work = create_sales_order(so)
            if no_work:
                finished.append(sales_order)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    _finish_committed_orders(finished)

def create_sales_order_routine(data):
    """Create orders from a center push. WMS is notified only after the batch
    commits — one failed order used to roll back siblings that had already fired
    their WMS finish call, leaving WMS holding orders that never existed here."""
    try:
        finished = []
        for so in data:
            sales_order, no_work = create_sales_order(so)
            if no_work:
                finished.append(sales_order)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    _finish_committed_orders(finished)

def create_sales_order(data):
    try:
        branch = branch_service.get_branch_by_code(data.get("pms_branch_code", None))
        urgency_level = _parse_urgency(data.get("urgency_level"))
        sales_order = SalesOrder(
            doc_entry = data.get("doc_entry"),
            doc_num = data.get("doc_num"),
            card_code = data.get("card_code"),
            card_name = data.get("card_name"),
            slp_code = data.get("slp_code"),
            slp_name = data.get("slp_name"),
            bpl_code = data.get("bpl_code"),
            bpl_name = data.get("bpl_name"),
            group_code = data.get("group_code"),
            group_name = data.get("group_name"),
            urgency_level = urgency_level,
            branch_id = branch.branch_id
        )

        for item in data.get("sales_item_list", []):
            sales_item = SalesItem(
                item_code=item.get("item_code"),
                item_name=item.get("item_name"),
                quantity=item.get("quantity"),
                order_line_num=item.get("order_line_num"),
                unit_name=item.get("unit_name", "Piece"),
                unit_id=item.get("unit_id"),
                unit_price=item.get("unit_price"),
                cost_price=item.get("cost_price"),
                doc_num=item.get("doc_num"),
                doc_entry=item.get("doc_entry"),
                center_sales_item_id=item.get("sales_item_id"),
                produce=item.get("produce", False),
                test=item.get("test", False),
                # column is NOT NULL and the SQLAlchemy default does not kick in for an
                # explicit None, so fall back to the same default the column declares
                item_group=item.get("category_name") or MANUFACTURED_ITEM_GROUP,
                branch_id = branch.branch_id
            )
            sales_order.sales_items.append(sales_item)

            for mat in item.get("material_list", []):
                if mat.get("order_line_num") is None:
                    raise MissingFieldsError("ไม่พบ order_line_num")
                material_list = MaterialList(
                    item_code=mat.get("item_code"),
                    item_name=mat.get("item_name"),
                    item_description=mat.get("item_description"),
                    quantity=mat.get("quantity"),
                    unit_name=mat.get("unit_name", "Piece"),
                    unit_id=mat.get("unit_id", 0),
                    unit_price=mat.get("unit_price"),
                    cost_price=mat.get("cost_price"),
                    item_group=mat.get("category_name") or "OTHER",
                    branch_id = branch.branch_id,
                    order_line_num = mat.get("order_line_num")
                )
                transaction_service.create_init_material_transaction(material_list, "INIT")
                sales_item.material_list.append(material_list)

        db.session.add(sales_order)
        no_work = _complete_no_work_items(sales_order)
        return sales_order, no_work
    except Exception:
        db.session.rollback()
        raise


def _complete_no_work_items(sales_order):
    """No item needs produce/test (or order has no items) -> nothing to work on.
    Marks those items COMPLETED and reports back so the caller can tell WMS the
    order is finished *after* the transaction commits. Returns True if it did.

    A Z-BOM item always counts as work even when center sends produce=False —
    it is built from a BOM, so auto-closing it would tell WMS the order is done
    while nothing was ever manufactured.

    Deliberately does not call WMS: an HTTP call cannot be rolled back, so firing
    it from inside the transaction can leave the order finished in WMS and absent
    here. See _finish_committed_orders.
    """
    items = sales_order.sales_items
    if not items:
        # An order with no lines is far more likely a truncated center payload than a
        # genuine no-work order — leave it INPROGRESS for a human rather than telling
        # WMS it is done. Escape hatch is DELETE /api/sales_order/cascade/<doc_num>.
        return False
    if any(si.produce or si.test or si.is_manufactured for si in items):
        return False
    for si in items:
        si.status = SalesItemStatus.COMPLETED
    return True


def _finish_committed_orders(sales_orders):
    """Tell WMS about no-work orders once they are safely committed.

    Runs one order per transaction and never re-raises: the batch is already
    committed, so raising would only lose the response. An order whose WMS call
    fails stays INPROGRESS with every item COMPLETED — exactly the state
    close_sales_order is built to retry, so the operator can finish it from the UI.
    """
    for sales_order in sales_orders:
        try:
            sales_order_finish(sales_order)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"WMS finish failed for doc_entry {sales_order.doc_entry} ({e}) — order left INPROGRESS for manual close")

def delete_sales_order_by_doc_num(doc_num, branch_id=None):
    try:
        sales_order = sales_order_repository.get_sales_order_by_doc_num(doc_num, branch_id=branch_id)
        doc_entry = sales_order.doc_entry
        sales_order_repository.delete_sales_order_cascade(sales_order)
        db.session.commit()
        return {"doc_num": doc_num, "doc_entry": doc_entry}
    except Exception:
        db.session.rollback()
        raise


def sales_order_finish(sales_order : SalesOrder):
    try:
        sales_order.status = SalesOrderStatus.COMPLETED
        res = wms_service.finish_sales_order(sales_order.doc_entry)
        print(f"res : {res}")
        print(f'{res.get("success", "LMAOOO")}')
        if res.get("success", False) == False:
            raise OuterServicesError(f"WMS ไม่สามารถจบ Order ได้ : {res.get('error')}")

    except Exception:
        raise


def close_sales_order(doc_entry, branch_id=None):
    """Manual close / retry lever for an order stuck at INPROGRESS.

    Gates, in order:
      1. every Z-BOM item must have finished production (work order exists, no open
         run, produced_qty >= quantity) — the produce flag is not trusted here;
      2. no-work items (produce=False and test=False) are marked COMPLETED, but only
         when they carry no unfinished work order / QC work order;
      3. every remaining item must already be COMPLETED.
    Then finishes through the same funnel as the normal path (sales_order_finish ->
    WMS). Raises if work is still pending, or if WMS finish fails (rolled back ->
    caller can retry once WMS has caught up).
    """
    try:
        sales_order = sales_order_repository.get_sales_order_by_doc_entry(doc_entry, branch_id=branch_id)
        if sales_order.status == SalesOrderStatus.COMPLETED:
            raise ValidationError("Order นี้ถูกปิดไปแล้ว")

        items = sales_item_repository.get_sales_items_by_doc_entry(doc_entry)
        if not items:
            raise ValidationError("Order นี้ไม่มีรายการขาย ปิด Order ไม่ได้")

        # Checked against every item, including ones already flagged COMPLETED: an item
        # that reached COMPLETED without production is exactly the bad state to catch.
        blocked = [f"{si.item_code}: {reason}" for si in items if (reason := si.production_blocker)]
        if blocked:
            raise ValidationError("ปิด Order ไม่ได้ — " + " | ".join(blocked))

        for si in items:
            if si.status == SalesItemStatus.COMPLETED or si.produce or si.test:
                continue
            if si.has_open_work:
                raise ValidationError(f"{si.item_code}: ยังมีใบสั่งผลิต/ใบสั่งเทสที่ยังไม่จบ ปิด Order ไม่ได้")
            si.status = SalesItemStatus.COMPLETED
            if si.work_order:
                si.work_order.status = WorkOrderStatus.COMPLETED
        db.session.flush()

        if sales_item_repository.has_incomplete_items(doc_entry):
            raise ValidationError("ยังมีรายการที่ต้องผลิต/เทสยังไม่เสร็จ ปิด Order ไม่ได้")

        sales_order_finish(sales_order)
        db.session.commit()
        return sales_order
    except Exception:
        db.session.rollback()
        raise
        
    