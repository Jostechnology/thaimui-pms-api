from app.con_sqlalchemy import ItemComponent, ComponentTemplateSectionData
from app.app import db
from sqlalchemy.orm import joinedload


def get_item_component_by_id(item_component_id):
    try:
        return ItemComponent.query.get(item_component_id)
    except Exception:
        raise


def get_item_component_with_sections(item_component_id):
    try:
        return ItemComponent.query.options(
            joinedload(ItemComponent.component_template_sections),
            joinedload(ItemComponent.material_usages),
        ).get(item_component_id)
    except Exception:
        raise


def save_section_data(item_component_id, template_id, sections_data):
    try:
        # Update template_id on item_component
        item = ItemComponent.query.get(item_component_id)
        if not item:
            return None
        item.component_template_id = template_id

        # Delete old section data for this component
        ComponentTemplateSectionData.query.filter_by(item_component_id=item_component_id).delete()

        # Insert new section data
        for s in sections_data:
            section = ComponentTemplateSectionData(
                item_component_id=item_component_id,
                section_type=s['section_type'],
                section_key=s['section_key'],
                data=s['data'],
            )
            db.session.add(section)

        return item
    except Exception:
        raise