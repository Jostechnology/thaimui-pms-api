from app.app import db
from app.con_sqlalchemy import PhaseTemplate, PhaseTemplateItem
from app.ma_sqlalchemy import PhaseTemplateSchema
from app.repositories import phase_template_repository


def get_phase_template_list(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = (data.get("search") or "").strip()
        result = phase_template_repository.get_phase_template_list(page, per_page, search)
        return {
            "items": PhaseTemplateSchema(many=True).dump(result.items),
            "page": page,
            "per_page": per_page,
            "total": result.total,
            "total_pages": result.pages,
        }
    except Exception:
        raise


def get_all_phase_templates():
    """Return all active templates for dropdowns."""
    try:
        templates = phase_template_repository.get_all_phase_templates_active()
        return PhaseTemplateSchema(many=True).dump(templates)
    except Exception:
        raise


def get_phase_template_by_id(phase_template_id):
    try:
        template = phase_template_repository.get_phase_template_by_id(phase_template_id)
        if not template:
            raise Exception(f"Phase template id {phase_template_id} not found")
        return PhaseTemplateSchema().dump(template)
    except Exception:
        raise


def create_phase_template(data):
    try:
        if not data.get("template_name", "").strip():
            raise Exception("template_name is required")

        items_data = data.get("items", [])
        if not items_data:
            raise Exception("At least one phase item is required")

        template = PhaseTemplate(
            template_name=data["template_name"].strip(),
            is_active=data.get("is_active", True),
        )

        for i, item in enumerate(items_data):
            if not item.get("phase_name", "").strip():
                raise Exception(f"phase_name is required for item {i + 1}")
            template_item = PhaseTemplateItem(
                phase_name=item["phase_name"].strip(),
                sort_order=item.get("sort_order", i),
                machine_type_id=item.get("machine_type_id") or None,
            )
            template.items.append(template_item)

        phase_template_repository.save_phase_template(template)
        db.session.commit()

        # Re-fetch to get full nested data
        fresh = phase_template_repository.get_phase_template_by_id(template.phase_template_id)
        return PhaseTemplateSchema().dump(fresh)
    except Exception:
        db.session.rollback()
        raise


def update_phase_template(phase_template_id, data):
    try:
        template = phase_template_repository.get_phase_template_by_id(phase_template_id)
        if not template:
            raise Exception(f"Phase template id {phase_template_id} not found")

        if "template_name" in data:
            template.template_name = data["template_name"].strip()
        if "is_active" in data:
            template.is_active = data["is_active"]

        if "items" in data:
            # Replace all items
            phase_template_repository.delete_template_items(phase_template_id)
            items_data = data.get("items", [])
            for i, item in enumerate(items_data):
                if not item.get("phase_name", "").strip():
                    raise Exception(f"phase_name is required for item {i + 1}")
                template_item = PhaseTemplateItem(
                    phase_template_id=phase_template_id,
                    phase_name=item["phase_name"].strip(),
                    sort_order=item.get("sort_order", i),
                    machine_type_id=item.get("machine_type_id") or None,
                )
                db.session.add(template_item)

        db.session.commit()

        fresh = phase_template_repository.get_phase_template_by_id(phase_template_id)
        return PhaseTemplateSchema().dump(fresh)
    except Exception:
        db.session.rollback()
        raise


def delete_phase_template(phase_template_id):
    try:
        template = phase_template_repository.get_phase_template_by_id(phase_template_id)
        if not template:
            raise Exception(f"Phase template id {phase_template_id} not found")
        template.is_active = False
        db.session.commit()
        return {"phase_template_id": phase_template_id, "message": "Deleted successfully"}
    except Exception:
        db.session.rollback()
        raise
