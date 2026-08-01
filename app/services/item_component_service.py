from app.con_sqlalchemy import (
    ComponentEditRequestStatus,
    ItemComponentVersion,
)
from app.repositories import (
    component_edit_request_repository,
    item_component_repository,
    item_component_version_repository,
    work_run_repository,
)
from app.app import db
from app.exception import AuthorizationError, NotFoundError, ValidationError
from app.services import document_generator_service, qc_work_order_service


LOCKED_MESSAGE = (
    "ใบสั่งผลิตนี้เริ่มการผลิตแล้ว ไม่สามารถแก้ไขเอกสารส่วนประกอบได้ "
    "กรุณาขออนุมัติจากฝ่ายผลิตก่อน"
)


# --- Lock state ---

def is_component_locked(item_component):
    """A component freezes once any WorkRun on its WorkOrder has been started."""
    return work_run_repository.has_started_run_for_work_order(item_component.work_order_id)


def get_component_lock_state(item_component):
    """Returns (is_locked, active_edit_request). An APPROVED request is the
    single-use key that lets one save through while locked."""
    locked = is_component_locked(item_component)
    if not locked:
        return False, None
    approved = component_edit_request_repository.get_approved_unconsumed(
        item_component.item_component_id
    )
    return True, approved


def _assert_editable(item_component):
    """Raise unless this component may be written right now. Returns the edit
    request that authorises the write (None when the component isn't locked)."""
    locked, approved = get_component_lock_state(item_component)
    if not locked:
        return None
    if not approved:
        raise AuthorizationError(LOCKED_MESSAGE)
    return approved


# --- Test section resolution ---
#
# The single source of truth for "is this section a test section". A section
# is a test section either because the template says so, or because this
# component's saved instance overrides that. Nothing else may re-derive this.

def resolve_test_section_keys(item_component) -> set:
    """Return the set of section_keys that resolve to "is a test section".

    Resolution per section_key: the per-instance override
    (ComponentTemplateSectionData.is_test_section) wins when it is not None;
    otherwise fall back to the template's own flag
    (ComponentTemplate.sections[].is_test_section); missing/absent -> False.

    Requires item_component.component_template and
    item_component.component_template_sections to already be loaded (e.g. via
    item_component_repository.get_item_component_for_document, or
    get_item_components_with_template_for_work_order) — both relationships are
    lazy='noload', so an unloaded one silently reads as None/[] rather than
    querying, which would just make this function wrong instead of raising.
    """
    template_flags = {}
    template = item_component.component_template
    if template and template.sections:
        for section in template.sections:
            key = section.get("key")
            if key is not None:
                template_flags[key] = bool(section.get("is_test_section"))

    overrides = {}
    for sd in (item_component.component_template_sections or []):
        overrides[sd.section_key] = sd.is_test_section

    resolved = set()
    for key in set(template_flags) | set(overrides):
        override = overrides.get(key)
        is_test = override if override is not None else template_flags.get(key, False)
        if is_test:
            resolved.add(key)
    return resolved


def component_has_test_section(item_component) -> bool:
    return bool(resolve_test_section_keys(item_component))


def work_order_declares_test_section(work_order_id):
    """True if ANY component of this WorkOrder currently resolves a test
    section. The QC auto-creation trigger is WorkOrder-scoped
    (QCWorkOrder.source_work_order_id points at the WorkOrder, not a single
    component), so this must check every component, not just the one that was
    just saved."""
    items = item_component_repository.get_item_components_with_template_for_work_order(work_order_id)
    return any(component_has_test_section(item) for item in items)


# --- Reads ---

def _stamp_lock_state(item, locked, approved):
    """Attach transient lock fields the schema dumps. Not DB columns."""
    item.is_locked = locked
    item.lock_reason = LOCKED_MESSAGE if locked else None
    item.active_edit_request = approved
    return item


def _stamp_test_section_state(item):
    """Attach transient test-section fields the schema dumps. Not DB columns."""
    keys = resolve_test_section_keys(item)
    item.test_section_keys = sorted(keys)
    item.has_test_section = bool(keys)
    return item


def _decorate_lock_state(item):
    locked, approved = get_component_lock_state(item)
    _stamp_lock_state(item, locked, approved)
    _stamp_test_section_state(item)
    return item


def decorate_work_order_components(work_order):
    """Stamp lock state and test-section state onto every component of a
    WorkOrder.

    Without this the components nested in WorkOrderSchemaDetail dump with no
    is_locked at all, which the FE would read as "editable". The lock is a
    WorkOrder-level fact, so it is resolved once rather than per component.
    """
    if not work_order or not work_order.item_components:
        return work_order

    locked = work_run_repository.has_started_run_for_work_order(work_order.work_order_id)
    for item in work_order.item_components:
        approved = (
            component_edit_request_repository.get_approved_unconsumed(item.item_component_id)
            if locked else None
        )
        _stamp_lock_state(item, locked, approved)
        _stamp_test_section_state(item)
    return work_order


def get_item_component_detail(item_component_id):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return _decorate_lock_state(item)
    except Exception:
        raise


def get_item_component_with_sections(item_component_id):
    try:
        item = item_component_repository.get_item_component_with_sections(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return _decorate_lock_state(item)
    except Exception:
        raise


def get_item_component_versions(item_component_id):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return item_component_version_repository.get_versions_by_item_component(item_component_id)
    except Exception:
        raise


def get_item_component_version(item_component_id, version_no):
    try:
        version = item_component_version_repository.get_version_by_no(item_component_id, version_no)
        if not version:
            raise NotFoundError(
                f"ไม่พบเวอร์ชัน {version_no} ของ Item Component {item_component_id}"
            )
        return version
    except Exception:
        raise


# --- Writes ---

def _snapshot_component(item, work_order, change_reason=None, edit_request=None):
    """Write the next immutable version row for `item` and fire its document.

    Caller owns the commit. `item` must already carry the new content and have
    its template/section/material relationships loaded.
    """
    next_no = item_component_version_repository.get_max_version_no(item.item_component_id) + 1
    snapshot = document_generator_service.build_component_snapshot(item)

    version = ItemComponentVersion(
        item_component_id=item.item_component_id,
        version_no=next_no,
        branch_id=item.branch_id,
        change_reason=change_reason,
        edit_request_id=edit_request.edit_request_id if edit_request else None,
        **snapshot,
    )
    item_component_version_repository.create_version(version)
    db.session.flush()

    item.doc_version = next_no
    document_generator_service.generate_component_document(version, work_order)

    if edit_request:
        edit_request.status = ComponentEditRequestStatus.CONSUMED
        edit_request.consumed_version_id = version.version_id

    return version


def _load_for_snapshot(item_component_id):
    item = item_component_repository.get_item_component_for_document(item_component_id)
    if not item:
        raise NotFoundError(f"ไม่พบข้อมูล Item Component {item_component_id}")
    if not item.work_order:
        raise NotFoundError(
            f"ไม่พบข้อมูล Work Order สำหรับ Item Component {item_component_id}"
        )
    return item


def create_initial_versions(work_order):
    """Write v1 for every component of a freshly created WorkOrder.

    Components start without a template — Sales fills that in later — but the
    version row must exist from the outset so a WorkRun always has something to
    pin, and so v1 records the material usage the order was created with.
    Caller owns the commit.
    """
    versions = []
    for item in work_order.item_components:
        versions.append(
            _snapshot_component(item, work_order, change_reason="สร้างใบสั่งผลิต")
        )

    # Components start without a template (see docstring above), so this is
    # always declared=False here today — but the reconcile still runs so
    # behaviour stays correct if that ever changes.
    declared = work_order_declares_test_section(work_order.work_order_id)
    qc_work_order_service.sync_component_declared_qc(work_order, declared)

    return versions


def save_component_section_data(item_component_id, data):
    try:
        template_id = data.get("component_template_id")
        sections_data = data.get("sections_data", [])
        change_reason = data.get("change_reason")

        if not template_id:
            raise ValidationError("กรุณาเลือก Template")

        existing = item_component_repository.get_item_component_by_id(item_component_id)
        if not existing:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        edit_request = _assert_editable(existing)

        item = item_component_repository.save_section_data(
            item_component_id, template_id, sections_data
        )
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        db.session.flush()

        item = _load_for_snapshot(item_component_id)
        _snapshot_component(item, item.work_order, change_reason, edit_request)

        # Reconcile the WorkOrder's auto QCWorkOrder against the test sections
        # this save just produced. item_component_service must not construct
        # a QCWorkOrder itself — qc_work_order_service owns that.
        declared = work_order_declares_test_section(item.work_order_id)
        qc_work_order_service.sync_component_declared_qc(item.work_order, declared)

        db.session.commit()

        return get_item_component_with_sections(item_component_id)
    except Exception:
        db.session.rollback()
        raise


def batch_save_component_section_data(items_data):
    try:
        if not items_data:
            raise ValidationError("ไม่มีข้อมูลสำหรับบันทึก")

        # Validate and authorise every entry before writing anything — a batch
        # must not half-apply and leave some components a version ahead.
        planned = []
        seen_ids = set()
        for entry in items_data:
            item_component_id = entry.get("item_component_id")
            template_id = entry.get("component_template_id")

            if not item_component_id:
                raise ValidationError("กรุณาระบุ item_component_id")
            if item_component_id in seen_ids:
                raise ValidationError(
                    f"item_component_id {item_component_id} ซ้ำกันใน batch เดียวกัน"
                )
            seen_ids.add(item_component_id)
            if not template_id:
                raise ValidationError(
                    f"กรุณาเลือก Template สำหรับ item_component_id {item_component_id}"
                )

            existing = item_component_repository.get_item_component_by_id(item_component_id)
            if not existing:
                raise NotFoundError(f"ไม่พบข้อมูล Item Component id {item_component_id}")

            edit_request = _assert_editable(existing)
            planned.append({
                "item_component_id": item_component_id,
                "template_id": template_id,
                "sections_data": entry.get("sections_data", []),
                "change_reason": entry.get("change_reason"),
                "edit_request": edit_request,
            })

        for plan in planned:
            item = item_component_repository.save_section_data(
                plan["item_component_id"], plan["template_id"], plan["sections_data"]
            )
            if not item:
                raise NotFoundError(
                    f"ไม่พบข้อมูล Item Component id {plan['item_component_id']}"
                )
        db.session.flush()

        touched_work_orders = {}
        for plan in planned:
            item = _load_for_snapshot(plan["item_component_id"])
            _snapshot_component(
                item, item.work_order, plan["change_reason"], plan["edit_request"]
            )
            touched_work_orders[item.work_order_id] = item.work_order

        # Reconcile once per distinct WorkOrder touched by this batch, after
        # every sibling component's save has landed — a batch may touch more
        # than one component of the same WorkOrder in a single request.
        for work_order_id, work_order in touched_work_orders.items():
            declared = work_order_declares_test_section(work_order_id)
            qc_work_order_service.sync_component_declared_qc(work_order, declared)

        db.session.commit()

        return [
            get_item_component_with_sections(plan["item_component_id"])
            for plan in planned
        ]
    except Exception:
        db.session.rollback()
        raise


def resend_component_document(item_component_id):
    """Re-send the current version's document. Never bumps doc_version."""
    try:
        version = document_generator_service.regenerate_current_component_document(
            item_component_id
        )
        db.session.commit()
        return version
    except Exception:
        db.session.rollback()
        raise
