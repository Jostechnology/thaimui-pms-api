import logging
import time
from datetime import datetime

from app.api_auth import _log_timer
from app.con_sqlalchemy import QCWorkOrder, QCForm, QCItem, SalesItem, TestSpec, TestSpecSourceType
from app.repositories import qc_work_order_repository, sales_item_repository, test_spec_repository
from app.app import db
from app.services import sales_item_service, sales_order_service, transaction_service
from app.exception import ValidationError
from app.utils import convert_start_date, convert_end_date, QTY_EPS

logger = logging.getLogger(__name__)

def get_all_qc_work_orders(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        filter = data.get("filter", None)
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_date = convert_start_date(start_date) if start_date else None
        end_date = convert_end_date(end_date) if end_date else None
        result = qc_work_order_repository.get_all_qc_work_orders(page, per_page, search, filter, start_date=start_date, end_date=end_date)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def get_qc_work_order_by_id(qc_work_order_id):
    try:
        _start = time.perf_counter()
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)
        _log_timer("GET qc_work_order_id", (time.perf_counter() - _start) * 1000, "", True)
        return qc
    except Exception:
        raise


def _parse_qc_form_date(raw):
    """Parse transfer_date / delivery_date from the QC form payload.

    Accepts 'YYYY-MM-DD' strings. None or '' means "no date" and becomes NULL
    rather than a parse error, since both fields are optional and independent
    of customer_receipt_number.
    """
    if raw is None or raw == "":
        return None
    try:
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"รูปแบบวันที่ไม่ถูกต้อง ต้องเป็น YYYY-MM-DD: {raw}")


def _build_qc_form(qc_work_order_id, data):
    return QCForm(
        qc_work_order_id=qc_work_order_id,
        std_ptt=data.get("ptt", False),
        std_chevron=data.get("chevron", False),
        std_valeur=data.get("valeur", False),
        std_ophir=data.get("ophir", False),
        std_three_spec=data.get("threeSpec", False),
        std_others=data.get("standardOthers", False),
        std_others_text=data.get("standardOthersText"),
        cert_inhouse=data.get("inHouse", False),
        cert_third_party=data.get("thirdParty", False),
        cert_ndt=data.get("ndt", False),
        cert_others=data.get("testingOthers", False),
        cert_others_text=data.get("testingOthersText"),
        serial_tag=data.get("serialTag", False),
        serial_imprint=data.get("serialImprint", False),
        serial_continue=data.get("continueSerial", False),
        serial_others=data.get("serialOthers", False),
        serial_others_text=data.get("serialOthersText"),
        general_remark=data.get("generalRemark"),
        details=data.get("details"),
        customer_receipt_number=data.get("customerReceiptNumber"),
        transfer_date=_parse_qc_form_date(data.get("transferDate")),
        delivery_date=_parse_qc_form_date(data.get("deliveryDate")),
    )


def _build_qc_items(qc_work_order_id, items_data):
    items = []
    for idx, item in enumerate(items_data or []):
        material_list_id = item.get("material_list_id", None)
        if material_list_id is None:
            raise ValidationError(f"ไม่พบ material_list_id สำหรับ {item.get('code', '-')}")
        items.append(QCItem(
            qc_work_order_id=qc_work_order_id,
            item_order=idx + 1,
            item_code=item.get("code"),
            description=item.get("description"),
            wll=item.get("wll"),
            quantity=str(item.get("quantity", "")),
            serial_no=item.get("serialNo"),
            item_remark=item.get("remark"),
            material_list_id=item.get("material_list_id")
        ))
    return items


def generate_qc_work_order_code(sales_item, qc_work_order_id):
    sales_item_order = sales_item_repository.get_sales_item_order_in_sales_order(
        sales_item.sales_item_id, sales_item.doc_entry
    )
    qc_order = qc_work_order_repository.get_qc_work_order_order_in_sales_item(
        qc_work_order_id, sales_item.sales_item_id
    )
    return f"{sales_item.doc_num}-{sales_item_order}-{qc_order}"


def _remove_component_section_spec(spec):
    """Delete one COMPONENT_SECTION TestSpec and its auto QCWorkOrder, after
    verifying no TestResult has ever been recorded against that QC (the
    results-guard). Raises ValidationError (Thai, mirrors the pre-unification
    message) and leaves everything untouched if results exist — the caller
    must let this roll back the whole save."""
    qc = qc_work_order_repository.get_qc_work_order_by_test_spec_id(spec.test_spec_id)
    if qc and qc.test_results:
        raise ValidationError(
            f"ไม่สามารถลบส่วนทดสอบได้ เนื่องจากใบสั่งเทส "
            f"{qc.qc_work_order_code or qc.qc_work_order_id} "
            "มีการบันทึกผลการทดสอบไปแล้ว"
        )
    if qc:
        # Not delete_qc_work_order — that commits and has no TestResult check
        # (already made above). Caller owns the commit here.
        qc_work_order_repository.delete_auto_qc_work_order(qc)
    test_spec_repository.delete_test_spec(spec)


def _ensure_component_section_auto_qc(spec, sales_item):
    """Ensure exactly one auto QCWorkOrder exists for a COMPONENT_SECTION
    TestSpec, full sales_item.quantity per spec (per-spec-full-qty decision —
    each declaring component independently requires the WHOLE quantity to be
    covered, not a share of one pool). E7: also reconciles quantity drift on
    an already-existing auto QC, not just create-if-missing."""
    qc = qc_work_order_repository.get_qc_work_order_by_test_spec_id(spec.test_spec_id)
    if qc:
        if abs((qc.quantity or 0) - sales_item.quantity) > QTY_EPS:
            qc.quantity = sales_item.quantity
        return qc

    qc = QCWorkOrder(
        sales_item_id=sales_item.sales_item_id,
        quantity=sales_item.quantity,
        test_spec_id=spec.test_spec_id,
        branch_id=sales_item.branch_id,
    )
    # Deliberately do NOT create a QCForm, any QCItem rows, or a
    # MaterialTransaction:
    #   - the component's test sections ARE the form — there is nothing
    #     left for QC staff to fill in
    #   - _build_qc_items hard-raises without material_list_id, which a
    #     component-declared QC never has (it isn't testing a specific
    #     material_list line, it's testing the component as documented)
    #   - the component's own material_usages already account for the
    #     material consumed, so a REMOVE MaterialTransaction here would
    #     double-count it
    qc = qc_work_order_repository.create_qc_work_order(qc)
    db.session.flush()
    qc.qc_work_order_code = generate_qc_work_order_code(sales_item, qc.qc_work_order_id)
    return qc


def sync_component_test_specs(work_order, declared_components):
    """Reconcile COMPONENT_SECTION TestSpecs (+ their auto QCWorkOrders) for
    `work_order` against which of its components currently resolve a test
    section, one spec per declaring component (S4: two declaring components
    must not collapse into one indistinguishable QC).

    `declared_components` is the per-component declaration list built by
    item_component_service.resolve_declared_test_components: dicts with
    item_component_id, component_name, section_keys, item_component_version_id.

    BE1 gate — read sales_item.test:
      * test == False: create/keep NO TestSpec, ever, regardless of what the
        components declare. Any pre-existing COMPONENT_SECTION specs get
        cleaned up (results-guard still applies). Returns
        {"skipped": True, "component_names": [...]} if there was anything to
        skip, else None.
      * test == True: reconcile specs to match declared_components exactly,
        upserting one COMPONENT_SECTION spec (+ auto QC) per declaring
        component and removing specs for components that no longer declare.
        Always returns None on this path (no notice).

    Called by item_component_service after a component-save's version
    snapshot is written — component saves must not construct a TestSpec or
    QCWorkOrder themselves, this is that boundary. Caller owns the commit:
    this never commits or rolls back, since it always runs inside the
    caller's component-save transaction.
    """
    sales_item = work_order.sales_item
    existing_specs = {
        spec.item_component_id: spec
        for spec in test_spec_repository.get_test_specs_by_sales_item(sales_item.sales_item_id)
        if spec.source_type == TestSpecSourceType.COMPONENT_SECTION
    }

    if not sales_item.test:
        for spec in list(existing_specs.values()):
            _remove_component_section_spec(spec)
        if declared_components:
            logger.info(
                "WorkOrder %s has %d component(s) declaring a test section but "
                "sales_item %s has test=False — no TestSpec created",
                work_order.work_order_id, len(declared_components), sales_item.sales_item_id,
            )
            return {
                "skipped": True,
                "component_names": [d["component_name"] for d in declared_components],
            }
        return None

    declared_by_component = {d["item_component_id"]: d for d in declared_components}

    # Remove specs for components that no longer declare a test section.
    for item_component_id, spec in list(existing_specs.items()):
        if item_component_id not in declared_by_component:
            _remove_component_section_spec(spec)
            del existing_specs[item_component_id]

    # Upsert a spec (+ auto QC) for every currently-declaring component.
    for item_component_id, decl in declared_by_component.items():
        spec = existing_specs.get(item_component_id)
        if spec is None:
            spec = TestSpec(
                sales_item_id=sales_item.sales_item_id,
                source_type=TestSpecSourceType.COMPONENT_SECTION,
                item_component_id=item_component_id,
                item_component_version_id=decl["item_component_version_id"],
                section_keys=decl["section_keys"],
                required_qty=sales_item.quantity,
                branch_id=sales_item.branch_id,
            )
            test_spec_repository.create_test_spec(spec)
            db.session.flush()
        else:
            spec.section_keys = decl["section_keys"]
            spec.item_component_version_id = decl["item_component_version_id"]
            spec.required_qty = sales_item.quantity

        _ensure_component_section_auto_qc(spec, sales_item)

    return None


def create_qc_work_order(data):
    try:
        sales_item_id = data.get("salesItemId") or data.get("sales_item_id")
        if not sales_item_id:
            raise Exception("กรุณาระบุ Sales Item")

        sales_item = sales_item_service.get_sales_item_by_id(sales_item_id)
        if not sales_item:
            raise Exception(f"ไม่พบ Sales Item ID: {sales_item_id}")

        material_usage_data = data.get("items", [])
        qc_quantity = data.get("salesItemQuantity", 1)

        planned_qty = sales_item.quantity
        # COMPONENT_SECTION specs each own their own full sales_item.quantity
        # independently (per-spec-full-qty decision) — they are not part of
        # this shared manual-QC pool, so only DIRECT-sourced QCs (or legacy
        # QCs with no spec at all) count against planned_qty here.
        component_section_spec_ids = {
            spec.test_spec_id
            for spec in test_spec_repository.get_test_specs_by_sales_item(sales_item_id)
            if spec.source_type == TestSpecSourceType.COMPONENT_SECTION
        }
        existing_qc_qty = sum(
            qc.quantity for qc in sales_item.qc_work_orders
            if qc.test_spec_id not in component_section_spec_ids
        )
        if existing_qc_qty + qc_quantity > planned_qty + QTY_EPS:
            raise ValidationError(f"จำนวน QC รวม ({existing_qc_qty + qc_quantity}) เกินจำนวนที่วางแผนผลิต ({planned_qty})")

        material_in_sales_order = sales_order_service.get_material_list_from_sales_order(sales_item.doc_entry)

        material_map = {m.material_list_id: m for m in material_in_sales_order}

        qc = QCWorkOrder(
            sales_item_id=sales_item_id,
            qc_date=data.get("qc_date"),
            qc_by=data.get("qc_by"),
            quantity=qc_quantity,
            remark=data.get("remark"),
            branch_id=sales_item.branch_id
        )
        qc = qc_work_order_repository.create_qc_work_order(qc)
        db.session.flush()

        qc.qc_work_order_code = generate_qc_work_order_code(sales_item, qc.qc_work_order_id)

        # Every QC now traces back to a TestSpec (DIRECT or COMPONENT_SECTION)
        # — a manually-created QC gets its own DIRECT spec here, no more bare
        # nullable-FK origin fork. item_component_id stays NULL (unique
        # constraint is on (sales_item_id, item_component_id) and MySQL does
        # not collide NULLs, so multiple DIRECT specs per sales_item are fine).
        spec = TestSpec(
            sales_item_id=sales_item_id,
            source_type=TestSpecSourceType.DIRECT,
            item_component_id=None,
            required_qty=qc_quantity,
            branch_id=sales_item.branch_id,
        )
        test_spec_repository.create_test_spec(spec)
        db.session.flush()
        qc.test_spec_id = spec.test_spec_id

        db.session.add(_build_qc_form(qc.qc_work_order_id, data))
        for item in _build_qc_items(qc.qc_work_order_id, data.get("items", [])):
            db.session.add(item)

        # Create MaterialTransaction(REMOVE) for each material consumed
        if material_usage_data:
            for usage in material_usage_data:
                material_list_id = usage.get("material_list_id", None)
                if material_list_id is None:
                    raise ValidationError("ไม่พบรายการวัตถุดิบเทส")
                material = material_map[material_list_id]
                transaction_service.create_material_transaction(
                    material, qc.qc_work_order_id, "REMOVE", float(usage.get("quantity"))
                )

        db.session.commit()
        db.session.refresh(qc)
        return qc
    except Exception:
        db.session.rollback()
        raise


def update_qc_work_order(qc_work_order_id, data):
    try:
        qc = qc_work_order_repository.get_qc_work_order_by_id(qc_work_order_id)

        if "qc_date" in data:
            qc.qc_date = data.get("qc_date")
        if "qc_by" in data:
            qc.qc_by = data.get("qc_by")
        print(data.get("quantity"))
        if "quantity" in data:
            qc.quantity = data.get("quantity")
        if "remark" in data:
            qc.remark = data.get("remark")

        if qc.qc_form:
            form = qc.qc_form
            form.std_ptt            = data.get("ptt", form.std_ptt)
            form.std_chevron        = data.get("chevron", form.std_chevron)
            form.std_valeur         = data.get("valeur", form.std_valeur)
            form.std_ophir          = data.get("ophir", form.std_ophir)
            form.std_three_spec     = data.get("threeSpec", form.std_three_spec)
            form.std_others         = data.get("standardOthers", form.std_others)
            form.std_others_text    = data.get("standardOthersText", form.std_others_text)
            form.cert_inhouse       = data.get("inHouse", form.cert_inhouse)
            form.cert_third_party   = data.get("thirdParty", form.cert_third_party)
            form.cert_ndt           = data.get("ndt", form.cert_ndt)
            form.cert_others        = data.get("testingOthers", form.cert_others)
            form.cert_others_text   = data.get("testingOthersText", form.cert_others_text)
            form.serial_tag         = data.get("serialTag", form.serial_tag)
            form.serial_imprint     = data.get("serialImprint", form.serial_imprint)
            form.serial_continue    = data.get("continueSerial", form.serial_continue)
            form.serial_others      = data.get("serialOthers", form.serial_others)
            form.serial_others_text = data.get("serialOthersText", form.serial_others_text)
            form.general_remark     = data.get("generalRemark", form.general_remark)
            form.details            = data.get("details", form.details)
            form.customer_receipt_number = data.get("customerReceiptNumber", form.customer_receipt_number)
            # Dates need parsing (and an explicit empty string must clear the
            # field to NULL), so these can't use the get-with-default idiom
            # above: data.get("transferDate", form.transfer_date) would fail
            # to parse the already-stored date object. Presence-check instead.
            if "transferDate" in data:
                form.transfer_date = _parse_qc_form_date(data.get("transferDate"))
            if "deliveryDate" in data:
                form.delivery_date = _parse_qc_form_date(data.get("deliveryDate"))
        else:
            db.session.add(_build_qc_form(qc_work_order_id, data))

        if "items" in data:
            for old_item in qc.qc_items:
                db.session.delete(old_item)
            db.session.flush()
            for item in _build_qc_items(qc_work_order_id, data.get("items", [])):
                db.session.add(item)

        db.session.commit()
        # db.session.refresh(qc)
        return qc
    except Exception:
        db.session.rollback()
        raise


def delete_qc_work_order(qc_work_order_id):
    try:
        qc_work_order_repository.delete_qc_work_order(qc_work_order_id)
        db.session.commit()
        return {"message": f"ลบ QC Work Order ID {qc_work_order_id} สำเร็จ"}
    except Exception:
        db.session.rollback()
        raise

def search_qc_work_orders(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = qc_work_order_repository.search_qc_work_orders(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise