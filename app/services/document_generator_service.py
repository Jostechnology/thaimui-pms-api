import copy
import logging
import threading

from app.exception import NotFoundError
from app.extensions import document_generator_service
from app.repositories import item_component_repository, item_component_version_repository
from app.services import item_component_service
from app.services.storage_service import get_as_base64

logger = logging.getLogger(__name__)

SERVICE_SOURCE = "thaimui-pms"


def _fire_and_forget(fn, *args):
    thread = threading.Thread(target=fn, args=args, daemon=True)
    thread.start()


def send_document(template, ref_no, data, path=None):
    if not document_generator_service:
        logger.warning("DocumentGeneratorService not configured, skipping document generation")
        return

    _fire_and_forget(
        document_generator_service.generate_document,
        SERVICE_SOURCE,
        template,
        ref_no,
        data,
        path,
    )


# --- Component document addressing ---
#
# Each version gets its own folder so the generator's `download/latest/<path>`
# route can still be used to fetch any historical version. Before versioning
# every save overwrote one shared folder, which made old versions unreachable.

def component_doc_ref_no(work_order, item_component_id, version_no):
    wo_code = work_order.work_order_code or work_order.doc_num
    return f"{wo_code}_comp{item_component_id}_v{version_no}"


def component_doc_path(work_order, item_component_id, version_no):
    wo_code = work_order.work_order_code or work_order.doc_num
    return f"work_orders/{wo_code}/components/{item_component_id}/v{version_no}"


# --- Snapshotting ---

def build_component_snapshot(item):
    """Freeze everything needed to re-render this component's document later.

    Template section images are stored as storage keys, not base64 — they are
    expanded at render time so the snapshot stays small.
    """
    template = item.component_template

    # Resolved (not raw) test-section state, so history shows when a test was
    # actually declared even though old snapshots predate this key entirely —
    # readers must treat a missing "is_test_section" as False, never crash.
    test_keys = item_component_service.resolve_test_section_keys(item)
    section_data_snapshot = [
        {
            "section_key": sd.section_key,
            "section_type": sd.section_type,
            "data": sd.data,
            "is_test_section": sd.section_key in test_keys,
        }
        for sd in (item.component_template_sections or [])
    ]

    material_usage_snapshot = []
    for usage in (item.material_usages or []):
        ml = usage.material_list
        material_usage_snapshot.append({
            "usage_id": usage.usage_id,
            "material_list_id": usage.material_list_id,
            "quantity_used": usage.quantity_used,
            "item_code": ml.item_code if ml else None,
            "item_name": ml.item_name if ml else None,
            "item_group": ml.item_group if ml else None,
            "unit_price": ml.unit_price if ml else None,
            "item_description": ml.item_description if ml else None,
        })

    return {
        "component_name": item.component_name,
        "remark": item.remark,
        "img_url": item.img_url,
        "component_template_id": item.component_template_id,
        "template_name": template.name if template else None,
        "sections_snapshot": copy.deepcopy(template.sections) if template and template.sections else [],
        "section_data_snapshot": section_data_snapshot,
        "material_usage_snapshot": material_usage_snapshot,
    }


def _expand_section_images(sections):
    """image_select options store storage keys; the generator needs inline data URIs."""
    expanded = copy.deepcopy(sections or [])
    for sec in expanded:
        if sec.get("type") != "image_select":
            continue
        for opt in sec.get("options") or []:
            key = opt.get("imageUrl")
            if not key or key.startswith("http") or key.startswith("data:"):
                continue
            b64 = get_as_base64(key.lstrip("/"))
            opt["imageUrl"] = f"data:image/jpeg;base64,{b64}"
    return expanded


def generate_component_document(version, work_order, raise_on_error=False):
    """Render the PDF for one frozen ItemComponentVersion.

    Idempotent: re-running regenerates the same ref_no at the same path, so a
    resend never bumps a version. Stamps ref_no/path onto the version row (the
    caller owns the commit).

    `raise_on_error=False` (the save path) keeps a document-generation failure
    from rolling back the version row — the snapshot is the durable record and
    the document can always be re-sent. The resend endpoint passes True so the
    user sees why it failed.
    """
    if not version.component_template_id:
        logger.info(
            "Component %s v%s has no template — skipping document generation",
            version.item_component_id, version.version_no,
        )
        return None

    # Stamped before any I/O so the version stays addressable even if the
    # render below fails and the document has to be re-sent later.
    ref_no = component_doc_ref_no(work_order, version.item_component_id, version.version_no)
    path = component_doc_path(work_order, version.item_component_id, version.version_no)
    version.doc_ref_no = ref_no
    version.doc_path = path

    try:
        _render_and_send_component_document(version, work_order, ref_no, path)
    except Exception:
        logger.exception(
            "Failed to generate document for component %s v%s",
            version.item_component_id, version.version_no,
        )
        if raise_on_error:
            raise
    return version


def _render_and_send_component_document(version, work_order, ref_no, path):
    form_data = {
        sd.get("section_key"): sd.get("data")
        for sd in (version.section_data_snapshot or [])
    }

    material_usages = [
        {
            "usage_id": mu.get("usage_id"),
            "quantity_used": mu.get("quantity_used"),
            "material_list": {
                "item_name": mu.get("item_name"),
                "item_code": mu.get("item_code"),
                "item_group": mu.get("item_group"),
                "unit_price": mu.get("unit_price"),
                "item_description": mu.get("item_description"),
            },
        }
        for mu in (version.material_usage_snapshot or [])
    ]

    sales_item = work_order.sales_item
    data = {
        "fr_no": ref_no,
        "template_name": version.template_name,
        "sections": _expand_section_images(version.sections_snapshot),
        "form_data": form_data,
        "work_order": {
            "doc_num": work_order.doc_num,
            "sales_item": {
                "item_name": sales_item.item_name if sales_item else None,
                "item_code": sales_item.item_code if sales_item else None,
                "quantity": sales_item.quantity if sales_item else None,
            },
        },
        "component": {
            "component_name": version.component_name,
            "material_usages": material_usages,
        },
        "version_no": version.version_no,
    }

    send_document(template="component_detail", ref_no=ref_no, data=data, path=path)


def regenerate_current_component_document(item_component_id):
    """Re-send the document for a component's CURRENT version. Does not create
    a new version — used by the resend endpoint."""
    item = item_component_repository.get_item_component_for_document(item_component_id)
    if not item:
        raise NotFoundError(f"ไม่พบข้อมูล Item Component {item_component_id}")

    work_order = item.work_order
    if not work_order:
        raise NotFoundError(f"ไม่พบข้อมูล Work Order สำหรับ Item Component {item_component_id}")

    version = item_component_version_repository.get_latest_version(item_component_id)
    if not version:
        raise NotFoundError(
            f"Item Component {item_component_id} ยังไม่มีเวอร์ชันเอกสาร — กรุณาบันทึกข้อมูลก่อน"
        )

    return generate_component_document(version, work_order, raise_on_error=True)
