from app.con_sqlalchemy import (
    ComponentEditRequestStatus,
    ItemComponentVersion,
)
from app.repositories import (
    component_edit_request_repository,
    item_component_repository,
    item_component_version_repository,
    work_order_repository,
    work_run_repository,
)
from app.app import db
from app.exception import AuthorizationError, NotFoundError, ValidationError
from app.services import document_generator_service, qc_work_order_service
from app.utils import QTY_EPS


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
    section. Kept for callers that only need the boolean; the QC/TestSpec
    reconcile itself needs the per-component detail — see
    resolve_declared_test_components."""
    items = item_component_repository.get_item_components_with_template_for_work_order(work_order_id)
    return any(component_has_test_section(item) for item in items)


def resolve_declared_test_components(work_order_id):
    """Every component of this WorkOrder that currently declares a test
    section, paired with its section_keys and latest version id.

    Feeds qc_work_order_service.sync_component_test_specs, which must react
    PER component (S4 fix — one TestSpec per declaring component), not just
    "does ANY component declare" (the old work_order_declares_test_section
    boolean that fed the pre-unification WorkOrder-level auto-QC sync).
    """
    items = item_component_repository.get_item_components_with_template_for_work_order(work_order_id)
    latest_versions = {
        v.item_component_id: v.version_id
        for v in item_component_version_repository.get_latest_versions_for_work_order(work_order_id)
    }
    declared = []
    for item in items:
        keys = resolve_test_section_keys(item)
        if not keys:
            continue
        declared.append({
            "item_component_id": item.item_component_id,
            "component_name": item.component_name,
            "section_keys": sorted(keys),
            "item_component_version_id": latest_versions.get(item.item_component_id),
        })
    return declared


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
    # always declared=[] here today — but the reconcile still runs so
    # behaviour stays correct if that ever changes.
    declared_components = resolve_declared_test_components(work_order.work_order_id)
    test_section_notice = qc_work_order_service.sync_component_test_specs(work_order, declared_components)
    # Transient — mutating the caller's own work_order object lets
    # work_order_service.create_work_order surface this in its response
    # without changing this function's return type (still a plain list of
    # versions, per the services-return-models convention).
    work_order.test_section_notice = test_section_notice

    return versions


def _write_section_data(item_component_id, template_id, sections_data):
    """Validate and persist one component's template pointer + section rows.

    Pure validate-and-write: no editability check, no snapshot, no commit —
    the caller owns the transaction and decides when to snapshot/commit so
    this is safely shareable across every entry point that writes sections.
    """
    if not template_id:
        raise ValidationError("กรุณาเลือก Template")

    item = item_component_repository.save_section_data(
        item_component_id, template_id, sections_data
    )
    if not item:
        raise NotFoundError("ไม่พบข้อมูล Item Component")
    return item


def _write_material_usage(item_component_id, work_order, material_usage_data):
    """Validate and full-replace one component's ComponentMaterialUsage set.

    Pure validate-and-write: no editability check, no snapshot, no commit —
    same sharing rationale as _write_section_data. `work_order` must already
    have sales_item.material_list and item_components[*].material_usages
    eager-loaded (work_order_repository.get_work_order_by_id's detail
    options), since both are lazy='noload' style — never traversed via
    implicit lazy select in this codebase.
    """
    material_map = {
        m.material_list_id: m
        for m in (work_order.sales_item.material_list if work_order.sales_item else [])
    }

    # Validate ownership, reject duplicates, coerce/validate quantities.
    seen_material_ids = set()
    cleaned_usage = []
    new_usage_by_material = {}
    for usage in material_usage_data:
        material_list_id = usage.get("material_list_id")

        if material_list_id not in material_map:
            raise NotFoundError(f"Material ID {material_list_id} ไม่ได้อยู่ใน Sales Item นี้")
        if material_list_id in seen_material_ids:
            raise ValidationError(f"Material ID {material_list_id} ซ้ำกันในรายการที่ส่งมา")
        seen_material_ids.add(material_list_id)

        try:
            quantity_used = float(usage.get("quantity_used"))
        except (TypeError, ValueError):
            raise ValidationError(f"จำนวนที่ใช้ของ Material ID {material_list_id} ไม่ถูกต้อง")
        if quantity_used <= 0:
            raise ValidationError(
                f"จำนวนที่ใช้ของ Material ID {material_list_id} ต้องมากกว่า 0"
            )

        new_usage_by_material[material_list_id] = quantity_used
        cleaned_usage.append({
            "material_list_id": material_list_id,
            "quantity_used": quantity_used,
        })

    # Over-allocation guard.
    #
    # We compare against MaterialList.quantity (the procured amount), not
    # remaining_num. remaining_num nets INIT against MaterialTransaction
    # rows, and the only REMOVE transactions ever posted against a
    # MaterialList come from QC test consumption (qc_work_order_service) —
    # production usage recorded here as ComponentMaterialUsage never posts
    # a MaterialTransaction at all. So remaining_num would (a) not reflect
    # any other component's allocation, defeating the point of this check,
    # and (b) falsely shrink availability by whatever a QC run already
    # consumed for testing, which has nothing to do with this correction.
    # Summing ComponentMaterialUsage across the WorkOrder ourselves and
    # comparing to the material's total procured quantity is the only
    # figure the codebase actually maintains that answers "would this
    # over-allocate the material this WorkOrder was given".
    totals = {}
    for comp in work_order.item_components:
        if comp.item_component_id == item_component_id:
            continue
        for u in (comp.material_usages or []):
            totals[u.material_list_id] = totals.get(u.material_list_id, 0) + u.quantity_used
    for material_list_id, quantity_used in new_usage_by_material.items():
        totals[material_list_id] = totals.get(material_list_id, 0) + quantity_used

    for material_list_id, total_used in totals.items():
        material = material_map.get(material_list_id)
        if material and total_used > material.quantity + QTY_EPS:
            raise ValidationError(
                f"Material ID {material_list_id} ({material.item_name}) ถูกใช้เกินจำนวนที่มีในใบสั่งขายนี้ "
                f"ต้องการรวมทั้งใบสั่งผลิต: {total_used}, มีทั้งหมด: {material.quantity}"
            )

    item = item_component_repository.replace_material_usage(item_component_id, cleaned_usage)
    if not item:
        raise NotFoundError("ไม่พบข้อมูล Item Component")
    return item


def save_component_section_data(item_component_id, data):
    try:
        template_id = data.get("component_template_id")
        sections_data = data.get("sections_data", [])
        change_reason = data.get("change_reason")

        existing = item_component_repository.get_item_component_by_id(item_component_id)
        if not existing:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        edit_request = _assert_editable(existing)

        _write_section_data(item_component_id, template_id, sections_data)
        db.session.flush()

        item = _load_for_snapshot(item_component_id)
        _snapshot_component(item, item.work_order, change_reason, edit_request)

        # Reconcile the WorkOrder's TestSpecs (+ auto QCWorkOrders) against the
        # test sections this save just produced. item_component_service must
        # not construct a TestSpec/QCWorkOrder itself — qc_work_order_service
        # owns that.
        declared_components = resolve_declared_test_components(item.work_order_id)
        test_section_notice = qc_work_order_service.sync_component_test_specs(
            item.work_order, declared_components
        )

        db.session.commit()

        result = get_item_component_with_sections(item_component_id)
        result.test_section_notice = test_section_notice
        return result
    except Exception:
        db.session.rollback()
        raise


def update_component_material_usage(item_component_id, data):
    """Full-replace a component's ComponentMaterialUsage set.

    Same lock/approval/versioning shape as save_component_section_data: the
    lock gate is checked before any write, the approval (if any) is consumed
    by the version snapshot that follows, and any failure rolls back both the
    delete and the insert together.
    """
    try:
        material_usage_data = data.get("material_usage", [])
        change_reason = data.get("change_reason")

        existing = item_component_repository.get_item_component_by_id(item_component_id)
        if not existing:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        edit_request = _assert_editable(existing)

        work_order = work_order_repository.get_work_order_by_id(existing.work_order_id)
        if not work_order:
            raise NotFoundError(
                f"ไม่พบข้อมูล Work Order สำหรับ Item Component {item_component_id}"
            )

        _write_material_usage(item_component_id, work_order, material_usage_data)
        db.session.flush()

        item = _load_for_snapshot(item_component_id)
        _snapshot_component(item, item.work_order, change_reason, edit_request)

        db.session.commit()

        return get_item_component_with_sections(item_component_id)
    except Exception:
        db.session.rollback()
        raise


def save_component(item_component_id, data):
    """Combined save: sections and/or material usage as ONE transaction, ONE
    editability check, ONE approval consumption, ONE version row, ONE
    document regeneration.

    Sections and materials belong to the same component version — the
    version snapshot (document_generator_service.build_component_snapshot)
    already freezes section_data_snapshot and material_usage_snapshot
    together, so splitting a single logical edit across two requests
    produces two version rows for what should be one, and — while locked —
    burns the single-use edit-request approval on the first request, 403ing
    the second. This endpoint is what the frontend must call for a locked
    component once both parts need to change in one edit.

    Key presence, not truthiness, controls which parts are touched:
    - "sections_data" absent  -> sections untouched (component_template_id
      is ignored too, since it only makes sense alongside a sections write).
    - "material_usage" absent -> material usage untouched.
    - Either key present with an empty list ([]) is a real instruction to
      clear that part, same as the standalone endpoints already treat it.
    Both keys may be omitted only if you truly have nothing to save, which is
    rejected below — a no-op combined save would otherwise still burn a
    single-use approval on a version identical to the current one.
    """
    try:
        has_sections = "sections_data" in data
        has_materials = "material_usage" in data
        if not has_sections and not has_materials:
            raise ValidationError("ไม่มีข้อมูลสำหรับบันทึก")

        template_id = data.get("component_template_id")
        sections_data = data.get("sections_data", [])
        material_usage_data = data.get("material_usage", [])
        change_reason = data.get("change_reason")

        existing = item_component_repository.get_item_component_by_id(item_component_id)
        if not existing:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        edit_request = _assert_editable(existing)

        work_order = None
        if has_materials:
            work_order = work_order_repository.get_work_order_by_id(existing.work_order_id)
            if not work_order:
                raise NotFoundError(
                    f"ไม่พบข้อมูล Work Order สำหรับ Item Component {item_component_id}"
                )

        if has_sections:
            _write_section_data(item_component_id, template_id, sections_data)
        if has_materials:
            _write_material_usage(item_component_id, work_order, material_usage_data)

        db.session.flush()

        item = _load_for_snapshot(item_component_id)
        _snapshot_component(item, item.work_order, change_reason, edit_request)

        # QC/TestSpec reconciliation only reacts to section changes — material
        # usage doesn't affect which sections declare as test sections.
        test_section_notice = None
        if has_sections:
            declared_components = resolve_declared_test_components(item.work_order_id)
            test_section_notice = qc_work_order_service.sync_component_test_specs(
                item.work_order, declared_components
            )

        db.session.commit()

        result = get_item_component_with_sections(item_component_id)
        result.test_section_notice = test_section_notice
        return result
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
        component_work_order = {}
        for plan in planned:
            item = _load_for_snapshot(plan["item_component_id"])
            _snapshot_component(
                item, item.work_order, plan["change_reason"], plan["edit_request"]
            )
            touched_work_orders[item.work_order_id] = item.work_order
            component_work_order[plan["item_component_id"]] = item.work_order_id

        # Reconcile once per distinct WorkOrder touched by this batch, after
        # every sibling component's save has landed — a batch may touch more
        # than one component of the same WorkOrder in a single request.
        notices_by_work_order = {}
        for work_order_id, work_order in touched_work_orders.items():
            declared_components = resolve_declared_test_components(work_order_id)
            notices_by_work_order[work_order_id] = qc_work_order_service.sync_component_test_specs(
                work_order, declared_components
            )

        db.session.commit()

        results = []
        for plan in planned:
            result = get_item_component_with_sections(plan["item_component_id"])
            result.test_section_notice = notices_by_work_order.get(
                component_work_order[plan["item_component_id"]]
            )
            results.append(result)
        return results
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
