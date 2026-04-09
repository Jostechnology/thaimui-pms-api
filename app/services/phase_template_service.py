from app.app import db
from app.con_sqlalchemy import PhaseTemplate, PhaseTemplateItem
from app.exception import NotFoundError, MissingFieldsError
from app.repositories import phase_template_repository


def get_phase_template_list(data):
    page = data.get("page", 1)
    per_page = data.get("per_page", 10)
    search = (data.get("search") or "").strip()
    return phase_template_repository.get_phase_template_list(page, per_page, search)


def get_all_phase_templates():
    return phase_template_repository.get_all_phase_templates_active()


def get_phase_template_by_id(phase_template_id):
    template = phase_template_repository.get_phase_template_by_id(phase_template_id)
    if not template:
        raise NotFoundError(f"Phase template id {phase_template_id} not found")
    return template


def create_phase_template(data):
    if not data.get("template_name", "").strip():
        raise MissingFieldsError("template_name is required")
    items_data = data.get("items", [])
    if not items_data:
        raise MissingFieldsError("At least one phase item is required")

    template = PhaseTemplate(
        template_name=data["template_name"].strip(),
        is_active=data.get("is_active", True),
    )

    for i, item in enumerate(items_data):
        if not item.get("phase_name", "").strip():
            raise MissingFieldsError(f"phase_name is required for item {i + 1}")
        template.items.append(PhaseTemplateItem(
            phase_name=item["phase_name"].strip(),
            sort_order=item.get("sort_order", i),
            machine_type_id=item.get("machine_type_id") or None,
        ))

    phase_template_repository.save_phase_template(template)
    db.session.commit()
    return phase_template_repository.get_phase_template_by_id(template.phase_template_id)


def update_phase_template(phase_template_id, data):
    template = phase_template_repository.get_phase_template_by_id(phase_template_id)
    if not template:
        raise NotFoundError(f"Phase template id {phase_template_id} not found")

    if "template_name" in data:
        template.template_name = data["template_name"].strip()
    if "is_active" in data:
        template.is_active = data["is_active"]

    if "items" in data:
        phase_template_repository.delete_template_items(phase_template_id)
        for i, item in enumerate(data["items"]):
            if not item.get("phase_name", "").strip():
                raise MissingFieldsError(f"phase_name is required for item {i + 1}")
            db.session.add(PhaseTemplateItem(
                phase_template_id=phase_template_id,
                phase_name=item["phase_name"].strip(),
                sort_order=item.get("sort_order", i),
                machine_type_id=item.get("machine_type_id") or None,
            ))

    db.session.commit()
    return phase_template_repository.get_phase_template_by_id(phase_template_id)


def delete_phase_template(phase_template_id):
    template = phase_template_repository.get_phase_template_by_id(phase_template_id)
    if not template:
        raise NotFoundError(f"Phase template id {phase_template_id} not found")
    template.is_active = False
    db.session.commit()
    return phase_template_repository.get_phase_template_by_id(phase_template_id)
