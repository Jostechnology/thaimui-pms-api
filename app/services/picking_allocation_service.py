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
        available = pri.quantity - committed
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
