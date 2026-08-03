from app.con_sqlalchemy import ItemComponent, ComponentTemplateSectionData, ComponentMaterialUsage, WorkOrder
from app.app import db
from sqlalchemy.orm import joinedload, selectinload


def get_item_component_by_id(item_component_id):
    try:
        query = db.session.query(ItemComponent).filter(
            ItemComponent.item_component_id == item_component_id
        )
        return query.first()
    except Exception:
        raise


def get_item_component_with_sections(item_component_id):
    try:
        query = db.session.query(ItemComponent).options(
            selectinload(ItemComponent.component_template),
            selectinload(ItemComponent.component_template_sections),
            selectinload(ItemComponent.material_usages)
                .selectinload(ComponentMaterialUsage.material_list),
        ).filter(ItemComponent.item_component_id == item_component_id)
        return query.first()
    except Exception:
        raise


def get_item_components_by_work_order(work_order_id):
    try:
        query = db.session.query(ItemComponent).filter(
            ItemComponent.work_order_id == work_order_id
        ).order_by(ItemComponent.item_component_id.asc())
        return query.all()
    except Exception:
        raise


def get_item_components_with_template_for_work_order(work_order_id):
    """All components of a WorkOrder with component_template + section-data
    eager-loaded — used to resolve whether ANY component of the WorkOrder
    currently declares a test section (item_component_service.resolve_test_section_keys
    needs both relationships loaded, never lazy-loaded)."""
    try:
        query = db.session.query(ItemComponent).options(
            selectinload(ItemComponent.component_template),
            selectinload(ItemComponent.component_template_sections),
        ).filter(ItemComponent.work_order_id == work_order_id)
        return query.all()
    except Exception:
        raise


def get_item_component_for_document(item_component_id):
    try:
        query = db.session.query(ItemComponent).options(
            selectinload(ItemComponent.component_template),
            selectinload(ItemComponent.component_template_sections),
            selectinload(ItemComponent.material_usages)
                .selectinload(ComponentMaterialUsage.material_list),
            selectinload(ItemComponent.work_order)
                .selectinload(WorkOrder.sales_item),
        ).populate_existing().filter(ItemComponent.item_component_id == item_component_id)
        return query.first()
    except Exception:
        raise


def save_section_data(item_component_id, template_id, sections_data):
    try:
        # Update template_id on item_component
        item_query = db.session.query(ItemComponent).filter(
            ItemComponent.item_component_id == item_component_id
        )
        item = item_query.first()
        if not item:
            return None
        item.component_template_id = template_id

        # Delete old section data for this component — history now lives in
        # t_item_component_version, so dropping the live rows is safe.
        delete_query = db.session.query(ComponentTemplateSectionData).filter(
            ComponentTemplateSectionData.item_component_id == item_component_id
        )
        delete_query.delete(synchronize_session='fetch')

        # Insert new section data
        for s in sections_data:
            section = ComponentTemplateSectionData(
                item_component_id=item_component_id,
                section_type=s['section_type'],
                section_key=s['section_key'],
                data=s['data'],
                # NULL (key absent) means "inherit the template's flag" — see
                # item_component_service.resolve_test_section_keys.
                is_test_section=s.get('is_test_section'),
            )
            db.session.add(section)

        return item
    except Exception:
        raise


def replace_material_usage(item_component_id, material_usage_data):
    """Full-replace ComponentMaterialUsage for one component: delete every
    existing row, insert the new set. Mirrors save_section_data's
    delete-then-insert shape. Caller owns flush/commit."""
    try:
        item_query = db.session.query(ItemComponent).filter(
            ItemComponent.item_component_id == item_component_id
        )
        item = item_query.first()
        if not item:
            return None

        delete_query = db.session.query(ComponentMaterialUsage).filter(
            ComponentMaterialUsage.item_component_id == item_component_id
        )
        delete_query.delete(synchronize_session='fetch')

        for usage in material_usage_data:
            db.session.add(ComponentMaterialUsage(
                item_component_id=item_component_id,
                material_list_id=usage['material_list_id'],
                quantity_used=usage['quantity_used'],
            ))

        return item
    except Exception:
        raise