from app.con_sqlalchemy import (
    PickingItemAdjustment, PickingItemAdjustmentReason,
    PickingRequest, PickingRequestItem, PickingRequestStatus,
)
from app.repositories import picking_request_repository
from app.services import document_code_service
from app.app import db
from app.exception import NotFoundError, ValidationError


def create_adjustment(picking_request_item_id, data):
    try:
        pri = picking_request_repository.get_picking_request_item_by_id(picking_request_item_id)
        if not pri:
            raise NotFoundError(f"PickingRequestItem {picking_request_item_id} not found")

        delta_qty = data.get("delta_qty")
        if delta_qty is None or delta_qty == 0:
            raise ValidationError("delta_qty ต้องไม่เป็น 0")

        raw_reason = (data.get("reason") or "").strip().upper()
        try:
            reason = PickingItemAdjustmentReason[raw_reason]
        except KeyError:
            allowed = [r.value for r in PickingItemAdjustmentReason]
            raise ValidationError(f"reason ไม่ถูกต้อง ต้องเป็นหนึ่งใน {allowed}")

        # Guard: adjustment must not push available below 0
        committed = picking_request_repository.get_total_committed_qty(picking_request_item_id)
        # current available = quantity + existing_adj_sum - committed
        # after this adj:   = quantity + (existing_adj_sum + delta_qty) - committed
        # = current_available + delta_qty
        current_available = pri.effective_quantity - committed
        if current_available + delta_qty < 0:
            raise ValidationError(
                f"ปรับได้สูงสุด -{current_available} (ปัจจุบันคงเหลือ {current_available})"
            )

        adj = PickingItemAdjustment(
            picking_request_item_id=picking_request_item_id,
            delta_qty=delta_qty,
            reason=reason,
            remark=data.get("remark"),
        )
        picking_request_repository.create_picking_item_adjustment(adj)
        db.session.commit()
        return adj
    except Exception:
        db.session.rollback()
        raise


def get_list(picking_request_item_id, data):
    pri = picking_request_repository.get_picking_request_item_by_id(picking_request_item_id)
    if not pri:
        raise NotFoundError(f"PickingRequestItem {picking_request_item_id} not found")

    return picking_request_repository.get_picking_item_adjustments_by_item(
        picking_request_item_id=picking_request_item_id,
        page=data.get("page", 1),
        per_page=data.get("per_page", 10),
    )


def get_list_by_picking_request(picking_request_id, data):
    pr = picking_request_repository.get_picking_request_by_id(picking_request_id)
    if not pr:
        raise NotFoundError(f"PickingRequest {picking_request_id} not found")

    return picking_request_repository.get_picking_item_adjustments_by_picking_request(
        picking_request_id=picking_request_id,
        page=data.get("page", 1),
        per_page=data.get("per_page", 10),
    )


def get_reallocate_options(source_pri_id):
    """Candidates user can pick as reallocate target. Same SO, matching item_code, source excluded."""
    source_pri = picking_request_repository.get_picking_request_item_by_id(source_pri_id)
    if not source_pri:
        raise NotFoundError(f"PickingRequestItem {source_pri_id} not found")
    source_pr = picking_request_repository.get_picking_request_by_id(source_pri.picking_request_id)
    if not source_pr or source_pr.status != PickingRequestStatus.SUCCESS:
        raise ValidationError("Source PickingRequest ต้องเป็น SUCCESS")

    return picking_request_repository.get_reallocate_options(source_pri, source_pr.doc_entry)


def _resolve_target_line(data, source_pri):
    """Pull target FK from payload. Lazy-imports to avoid cycles.
    Returns (target_pri_id, target_sales_item_id, target_material_list_id, target_line_obj)."""
    from app.repositories import sales_item_repository, material_list_repository
    from app.con_sqlalchemy import SalesItem, MaterialList

    to_pri_id = data.get("to_picking_request_item_id")
    to_si_id = data.get("to_sales_item_id")
    to_ml_id = data.get("to_material_list_id")

    provided = [x for x in (to_pri_id, to_si_id, to_ml_id) if x is not None]
    if len(provided) != 1:
        raise ValidationError(
            "ต้องระบุปลายทางเพียงรายการเดียว: to_picking_request_item_id, to_sales_item_id, หรือ to_material_list_id"
        )

    if to_si_id is not None:
        si = db.session.query(SalesItem).filter(SalesItem.sales_item_id == to_si_id).first()
        if not si:
            raise NotFoundError(f"SalesItem {to_si_id} not found")
        return None, to_si_id, None, si
    if to_ml_id is not None:
        ml = db.session.query(MaterialList).filter(MaterialList.material_list_id == to_ml_id).first()
        if not ml:
            raise NotFoundError(f"MaterialList {to_ml_id} not found")
        return None, None, to_ml_id, ml
    return to_pri_id, None, None, None


def _create_reallocation_pr(doc_entry, target_line, qty, remark):
    """Spin a new PR marked is_reallocation=True, status=SUCCESS, with a single PRI for target line."""
    from app.con_sqlalchemy import SalesItem, MaterialList

    pr = PickingRequest(
        picking_request_code=document_code_service.generate_number("PR"),
        doc_entry=doc_entry,
        status=PickingRequestStatus.SUCCESS,
        is_reallocation=True,
        remark=remark,
    )
    picking_request_repository.create_picking_request(pr)
    db.session.flush()

    if isinstance(target_line, SalesItem):
        pri = PickingRequestItem(
            picking_request_id=pr.picking_request_id,
            sales_item_id=target_line.sales_item_id,
            material_list_id=None,
            order_line_num=target_line.order_line_num,
            item_code=target_line.item_code,
            item_name=target_line.item_name,
            quantity=0,
            unit=target_line.unit_name,
        )
    else:
        pri = PickingRequestItem(
            picking_request_id=pr.picking_request_id,
            sales_item_id=None,
            material_list_id=target_line.material_list_id,
            order_line_num=target_line.order_line_num,
            item_code=target_line.item_code,
            item_name=target_line.item_name,
            quantity=0,
            unit=target_line.unit_name,
        )
    db.session.add(pri)
    db.session.flush()
    return pr, pri


def reallocate(source_pri_id, data):
    """
    Transfer qty from source PRI to a target PRI within the same SO.
    Applies paired adjustments (source -qty, target +qty). If target line has no SUCCESS PRI,
    spins a new reallocation PR (status=SUCCESS, is_reallocation=True) with a new PRI holding
    the transferred qty instead of +adjustment.

    Body:
        qty: int (>0, <= source available)
        Exactly one of:
            to_picking_request_item_id
            to_sales_item_id
            to_material_list_id
        so_doc_entry: int — required when to_sales_item_id or to_material_list_id is given
        remark: optional

    Returns a dict describing the outcome.
    """
    try:
        qty = data.get("qty")
        if not qty or qty <= 0:
            raise ValidationError("qty ต้องมากกว่า 0")
        remark = data.get("remark")

        source_pri = picking_request_repository.get_picking_request_item_by_id(source_pri_id)
        if not source_pri:
            raise NotFoundError(f"PickingRequestItem {source_pri_id} not found")
        source_pr = picking_request_repository.get_picking_request_by_id(source_pri.picking_request_id)
        if not source_pr or source_pr.status != PickingRequestStatus.SUCCESS:
            raise ValidationError("Source PickingRequest ต้องเป็น SUCCESS")

        source_committed = picking_request_repository.get_total_committed_qty(source_pri_id)
        source_available = source_pri.effective_quantity - source_committed
        if qty > source_available:
            raise ValidationError(
                f"Source คงเหลือ {source_available} แต่ขอโอน {qty}"
            )

        to_pri_id, to_si_id, to_ml_id, target_line = _resolve_target_line(data, source_pri)

        target_pri = None
        target_adjustment = None
        new_reallocation_pr = None

        # --- Path A: explicit target PRI ---
        if to_pri_id is not None:
            target_pri = picking_request_repository.get_picking_request_item_by_id(to_pri_id)
            if not target_pri:
                raise NotFoundError(f"Target PickingRequestItem {to_pri_id} not found")
            if target_pri.picking_request_item_id == source_pri.picking_request_item_id:
                raise ValidationError("Target ต้องไม่ใช่ตัวเดียวกับ source")
            target_pr = picking_request_repository.get_picking_request_by_id(target_pri.picking_request_id)
            if not target_pr or target_pr.status != PickingRequestStatus.SUCCESS:
                raise ValidationError("Target PickingRequest ต้องเป็น SUCCESS")
            if source_pr.doc_entry != target_pr.doc_entry:
                raise ValidationError("Target ต้องอยู่ Sales Order เดียวกับ source")
            if target_pri.sales_item_id is None and target_pri.material_list_id is None:
                raise ValidationError("Target PRI ต้องผูกกับ SalesItem หรือ MaterialList")
            if source_pri.item_code != target_pri.item_code:
                raise ValidationError(
                    f"item_code ไม่ตรงกัน: source {source_pri.item_code} vs target {target_pri.item_code}"
                )
            target_adjustment = PickingItemAdjustment(
                picking_request_item_id=target_pri.picking_request_item_id,
                delta_qty=qty,
                reason=PickingItemAdjustmentReason.REALLOCATE,
                remark=remark,
                counterparty_picking_request_item_id=source_pri.picking_request_item_id,
            )
            picking_request_repository.create_picking_item_adjustment(target_adjustment)

        # --- Path B: line FK given, look up existing SUCCESS PRI ---
        else:
            so_doc_entry = data.get("so_doc_entry")
            if so_doc_entry is None:
                raise ValidationError("so_doc_entry จำเป็นต้องระบุเมื่อใช้ to_sales_item_id หรือ to_material_list_id")

            if to_si_id is not None:
                if target_line.doc_entry != so_doc_entry:
                    raise ValidationError(f"SalesItem {to_si_id} ไม่ได้อยู่ใน Sales Order นี้")
            else:
                from app.con_sqlalchemy import SalesItem as _SI
                parent_si = db.session.query(_SI).filter(
                    _SI.sales_item_id == target_line.sales_item_id,
                    _SI.doc_entry == so_doc_entry,
                ).first()
                if not parent_si:
                    raise ValidationError(f"MaterialList {to_ml_id} ไม่ได้อยู่ใน Sales Order นี้")

            if source_pri.item_code != target_line.item_code:
                raise ValidationError(
                    f"item_code ไม่ตรงกัน: source {source_pri.item_code} vs target line {target_line.item_code}"
                )

            existing = picking_request_repository.get_success_pris_for_line(
                so_doc_entry,
                sales_item_id=to_si_id,
                material_list_id=to_ml_id,
            )
            if len(existing) > 1:
                raise ValidationError(
                    "มี PickingRequestItem หลายรายการสำหรับ line นี้ ต้องระบุ to_picking_request_item_id"
                )
            if len(existing) == 1:
                target_pri = existing[0]
                target_adjustment = PickingItemAdjustment(
                    picking_request_item_id=target_pri.picking_request_item_id,
                    delta_qty=qty,
                    reason=PickingItemAdjustmentReason.REALLOCATE,
                    remark=remark,
                    counterparty_picking_request_item_id=source_pri.picking_request_item_id,
                )
                picking_request_repository.create_picking_item_adjustment(target_adjustment)
            else:
                new_reallocation_pr, target_pri = _create_reallocation_pr(
                    so_doc_entry, target_line, qty, remark
                )
                target_adjustment = PickingItemAdjustment(
                    picking_request_item_id=target_pri.picking_request_item_id,
                    delta_qty=qty,
                    reason=PickingItemAdjustmentReason.REALLOCATE,
                    remark=remark,
                    counterparty_picking_request_item_id=source_pri.picking_request_item_id,
                )
                picking_request_repository.create_picking_item_adjustment(target_adjustment)

        # --- Source -qty adjustment (always) ---
        source_adjustment = PickingItemAdjustment(
            picking_request_item_id=source_pri.picking_request_item_id,
            delta_qty=-qty,
            reason=PickingItemAdjustmentReason.REALLOCATE,
            remark=remark,
            counterparty_picking_request_item_id=target_pri.picking_request_item_id,
        )
        picking_request_repository.create_picking_item_adjustment(source_adjustment)

        db.session.commit()

        return {
            "qty": qty,
            "source_picking_request_item_id": source_pri.picking_request_item_id,
            "source_adjustment_id": source_adjustment.id,
            "target_picking_request_item_id": target_pri.picking_request_item_id,
            "target_adjustment_id": target_adjustment.id if target_adjustment else None,
            "created_reallocation_pr": (
                {
                    "picking_request_id": new_reallocation_pr.picking_request_id,
                    "picking_request_code": new_reallocation_pr.picking_request_code,
                }
                if new_reallocation_pr else None
            ),
        }
    except Exception:
        db.session.rollback()
        raise
