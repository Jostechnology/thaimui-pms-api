from app.services import picking_request_service


def _require_id(payload):
    pr_id = payload.get("picking_request_id")
    if not pr_id:
        # ValidationError would be caught as AppException and retried — that's fine;
        # a malformed message will eventually be parked.
        from app.exception import ValidationError
        raise ValidationError("picking_request_id is required")
    return int(pr_id)


def handle_status_picking(payload):
    """WMS acknowledges and is actively picking."""
    pr_id = _require_id(payload)
    picking_request_service.mark_picking(pr_id, payload)


def handle_status_sent(payload):
    """WMS has dispatched the items."""
    pr_id = _require_id(payload)
    picking_request_service.mark_sent(pr_id, payload)
