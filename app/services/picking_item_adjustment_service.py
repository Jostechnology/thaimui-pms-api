from app.con_sqlalchemy import PickingItemAdjustment, PickingItemAdjustmentReason
from app.repositories import picking_request_repository
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
        current_available = pri.quantity - committed
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
