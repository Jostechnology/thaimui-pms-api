from app.con_sqlalchemy import PhaseTemplate, PhaseTemplateItem
from app.app import db
from sqlalchemy import or_
from sqlalchemy.orm import selectinload


def get_phase_template_list(page, per_page, search, is_active=True):
    try:
        query = db.session.query(PhaseTemplate).options(
            selectinload(PhaseTemplate.items).selectinload(PhaseTemplateItem.machine_type)
        )
        if is_active is not None:
            query = query.filter(PhaseTemplate.is_active == is_active)
        if search:
            query = query.filter(PhaseTemplate.template_name.ilike(f"%{search}%"))
        query = query.order_by(PhaseTemplate.phase_template_id.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
    except Exception:
        raise


def get_phase_template_by_id(phase_template_id):
    try:
        return (
            db.session.query(PhaseTemplate)
            .options(
                selectinload(PhaseTemplate.items).selectinload(PhaseTemplateItem.machine_type)
            )
            .filter(PhaseTemplate.phase_template_id == phase_template_id)
            .first()
        )
    except Exception:
        raise


def get_all_phase_templates_active():
    """Return all active phase templates for dropdowns."""
    try:
        return (
            db.session.query(PhaseTemplate)
            .options(
                selectinload(PhaseTemplate.items).selectinload(PhaseTemplateItem.machine_type)
            )
            .filter(PhaseTemplate.is_active == True)
            .order_by(PhaseTemplate.template_name)
            .all()
        )
    except Exception:
        raise


def save_phase_template(template):
    try:
        db.session.add(template)
        db.session.flush()
        return template
    except Exception:
        raise


def delete_template_items(phase_template_id):
    try:
        PhaseTemplateItem.query.filter_by(phase_template_id=phase_template_id).delete()
        db.session.flush()
    except Exception:
        raise
