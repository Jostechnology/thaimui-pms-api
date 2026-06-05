"""
Shared FIFO allocation helper for picking request items.

Both TestResult (non-produced sales items) and WorkRun (materials) use the same
FIFO allocation logic against PickingRequestItems where the parent PR is SUCCESS.

The committed-qty getter must sum across ALL consumer tables (TestResultPickingItem +
WorkRunPickingItem) so a single picking item cannot be double-allocated.
"""
from app.repositories import picking_request_repository
from app.exception import ValidationError


def allocate_fifo(candidates, needed_qty):
    """
    FIFO-allocate needed_qty from a list of PickingRequestItem candidates.

    Args:
        candidates: PickingRequestItem instances ordered by picking_request_item_id ASC.
        needed_qty: total quantity to allocate.

    Returns:
        list of (picking_request_item_id, qty) tuples.

    Raises:
        ValidationError if pool is insufficient.
    """
    allocations = []
    remaining = needed_qty

    for pri in candidates:
        if remaining <= 0:
            break
        committed = picking_request_repository.get_total_committed_qty(pri.picking_request_item_id)
        available = pri.effective_quantity - committed
        if available <= 0:
            continue
        take = min(available, remaining)
        allocations.append((pri.picking_request_item_id, take))
        remaining -= take

    if remaining > 0:
        raise ValidationError(
            f"วัตถุดิบในคลังไม่พอ: ต้องการ {needed_qty} แต่มีเพียง {needed_qty - remaining}"
        )

    return allocations


def allocate_manual(manual_sources, needed_qty):
    """
    Validate and apply manual allocation from operator-chosen picking items.

    Args:
        manual_sources: list of dicts with {picking_request_item_id, qty}.
        needed_qty: total quantity required.

    Returns:
        list of (picking_request_item_id, qty) tuples.

    Raises:
        ValidationError if total qty doesn't match needed or picking item has insufficient availability.
    """
    total_manual = sum(s["qty"] for s in manual_sources)
    if total_manual != needed_qty:
        raise ValidationError(
            f"จำนวนที่ระบุไม่ตรง: ต้องการ {needed_qty} แต่ระบุมา {total_manual}"
        )

    allocations = []
    for s in manual_sources:
        pri_id = s["picking_request_item_id"]
        qty = s["qty"]
        if qty <= 0:
            raise ValidationError(f"จำนวนต้องมากกว่า 0 (picking_request_item_id={pri_id})")

        pri = picking_request_repository.get_picking_request_item_by_id(pri_id)
        if not pri:
            raise ValidationError(f"ไม่พบ Picking Request Item {pri_id}")

        committed = picking_request_repository.get_total_committed_qty(pri_id)
        available = pri.effective_quantity - committed
        if qty > available:
            raise ValidationError(
                f"Picking Item {pri_id} ({pri.item_code}) มีเหลือ {available} แต่ระบุ {qty}"
            )
        allocations.append((pri_id, qty))

    return allocations
