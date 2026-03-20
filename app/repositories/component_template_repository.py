from app.con_sqlalchemy import ComponentTemplate
from app.app import db
from sqlalchemy import or_


def get_all_templates(page, limit, search):
    try:
        query = db.session.query(ComponentTemplate)
        if search:
            query = query.filter(ComponentTemplate.name.ilike(f"%{search}%"))
        query = query.order_by(ComponentTemplate.component_template_id.desc())
        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise


def get_template_by_id(template_id):
    try:
        template = db.session.query(ComponentTemplate).filter(
            ComponentTemplate.component_template_id == template_id
        ).first()
        return template
    except Exception:
        raise


def create_template(template):
    try:
        db.session.add(template)
        db.session.flush()
        return template
    except Exception:
        raise


def update_template(template):
    try:
        db.session.merge(template)
        db.session.flush()
        return template
    except Exception:
        raise


def delete_template(template_id):
    try:
        template = db.session.query(ComponentTemplate).filter(
            ComponentTemplate.component_template_id == template_id
        ).first()
        if template:
            db.session.delete(template)
            db.session.flush()
        return template
    except Exception:
        raise
