import logging
import threading

from app.exception import NotFoundError
from app.extensions import document_generator_service
from app.repositories import item_component_repository

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


def generate_component_detail(item_component_id):
    try:
        item = item_component_repository.get_item_component_for_document(item_component_id)
        if not item:
            raise NotFoundError(f"ไม่พบข้อมูล Item Component {item_component_id}")

        template = item.component_template
        if not template:
            print(f"Returned : No template : {template} / {type(template)} | item_component_id : {item_component_id}")
            return

        work_order = item.work_order
        if not work_order:
            raise NotFoundError(f"ไม่พบข้อมูล Work Order สำหรับ Item Component {item_component_id}")

        # Build sections from template
        sections = template.sections if template.sections else []

        # Build form_data from section data
        form_data = {}
        for section_data in item.component_template_sections:
            form_data[section_data.section_key] = section_data.data

        # Build material table data
        material_usages = []
        for usage in item.material_usages:
            ml = usage.material_list
            material_usages.append({
                "usage_id": usage.usage_id,
                "quantity_used": usage.quantity_used,
                "material_list": {
                    "item_name": ml.item_name if ml else None,
                    "item_code": ml.item_code if ml else None,
                    "item_group": ml.item_group if ml else None,
                    "unit_price": ml.unit_price if ml else None,
                    "item_description": ml.item_description if ml else None,
                }
            })

        # Build work order context
        sales_item = work_order.sales_item
        work_order_data = {
            "doc_num": work_order.doc_num,
            "sales_item": {
                "item_name": sales_item.item_name if sales_item else None,
                "item_code": sales_item.item_code if sales_item else None,
                "item_num": sales_item.item_num if sales_item else None,
            }
        }

        # Increment version on the component
        item.doc_version = (item.doc_version or 0) + 1
        version = item.doc_version

        wo_code = work_order.work_order_code or work_order.doc_num
        ref_no = f"{wo_code}_comp{item.item_component_id}_v{version}"
        path = f"work_orders/{wo_code}/components/{item.item_component_id}"

        data = {
            "fr_no": ref_no,
            "template_name": template.name,
            "sections": sections,
            "form_data": form_data,
            "work_order": work_order_data,
            "component": {
                "component_name": item.component_name,
                "material_usages": material_usages,
            }
        }
        
        send_document(
            template="component_detail",
            ref_no=ref_no,
            data=data,
            path=path,
        )
    except Exception as e:
        print(f"Error : {str(e)}")
