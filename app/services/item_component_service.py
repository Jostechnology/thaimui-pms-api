from app.con_sqlalchemy import ItemComponent
from app.ma_sqlalchemy import (
    ItemComponentSchema,
)
from app.repositories import item_component_repository
from app.app import db
from app.exception import NotFoundError, ValidationError


def get_item_component_detail(item_component_id):
    try:
        item = item_component_repository.get_item_component_by_id(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return ItemComponentSchema().dump(item)
    except Exception:
        raise


def get_item_component_with_sections(item_component_id):
    try:
        item = item_component_repository.get_item_component_with_sections(item_component_id)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")
        return ItemComponentSchema().dump(item)
    except Exception:
        raise


def save_component_section_data(item_component_id, data):
    try:
        template_id = data.get("component_template_id")
        sections_data = data.get("sections_data", [])

        if not template_id:
            raise ValidationError("กรุณาเลือก Template")

        item = item_component_repository.save_section_data(item_component_id, template_id, sections_data)
        if not item:
            raise NotFoundError("ไม่พบข้อมูล Item Component")

        db.session.commit()

        # Re-fetch with sections loaded
        return get_item_component_with_sections(item_component_id)
    except Exception:
        db.session.rollback()
        raise


def batch_save_component_section_data(items_data):
    try:
        for entry in items_data:
            item_component_id = entry.get("item_component_id")
            template_id = entry.get("component_template_id")
            sections_data = entry.get("sections_data", [])

            if not item_component_id:
                raise ValidationError("กรุณาระบุ item_component_id")
            if not template_id:
                raise ValidationError(f"กรุณาเลือก Template สำหรับ item_component_id {item_component_id}")

            item = item_component_repository.save_section_data(item_component_id, template_id, sections_data)
            if not item:
                raise NotFoundError(f"ไม่พบข้อมูล Item Component id {item_component_id}")

        db.session.commit()

        results = []
        for entry in items_data:
            results.append(get_item_component_with_sections(entry["item_component_id"]))
        return results
    except Exception:
        db.session.rollback()
        raise