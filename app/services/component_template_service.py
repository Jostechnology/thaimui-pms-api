from app.con_sqlalchemy import ComponentTemplate
from app.repositories import component_template_repository
from app.app import db
from app.exception import NotFoundError, ValidationError


def get_all_templates(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = component_template_repository.get_all_templates(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def get_template_by_id(template_id):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")
        return template
    except Exception:
        raise


def create_template(data):
    try:
        name = data.get("name")
        sections = data.get("sections")

        if not name:
            raise ValidationError("Template name is required")
        if not sections:
            raise ValidationError("Template sections are required")

        template = ComponentTemplate(
            name=name,
            sections=sections,
        )
        component_template_repository.create_template(template)
        db.session.commit()
        return template
    except Exception:
        db.session.rollback()
        raise


def update_template(template_id, data):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        if "name" in data:
            template.name = data["name"]
        if "sections" in data:
            template.sections = data["sections"]

        component_template_repository.update_template(template)
        db.session.commit()
        return template
    except Exception:
        db.session.rollback()
        raise


def delete_template(template_id):
    try:
        template = component_template_repository.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        component_template_repository.delete_template(template_id)
        db.session.commit()
        return template
    except Exception:
        db.session.rollback()
        raise
