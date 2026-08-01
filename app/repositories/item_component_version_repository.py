from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import ItemComponent, ItemComponentVersion


def create_version(version):
    try:
        db.session.add(version)
        return version
    except Exception:
        raise


def get_version_by_id(version_id):
    try:
        query = db.session.query(ItemComponentVersion).filter(
            ItemComponentVersion.version_id == version_id
        )
        return query.first()
    except Exception:
        raise


def get_version_detail(version_id):
    try:
        query = db.session.query(ItemComponentVersion).options(
            selectinload(ItemComponentVersion.item_component),
            selectinload(ItemComponentVersion.edit_request),
        ).filter(ItemComponentVersion.version_id == version_id)
        return query.first()
    except Exception:
        raise


def get_version_by_no(item_component_id, version_no):
    try:
        query = db.session.query(ItemComponentVersion).filter(
            ItemComponentVersion.item_component_id == item_component_id,
            ItemComponentVersion.version_no == version_no,
        )
        return query.first()
    except Exception:
        raise


def get_versions_by_item_component(item_component_id):
    try:
        query = db.session.query(ItemComponentVersion).filter(
            ItemComponentVersion.item_component_id == item_component_id
        ).order_by(ItemComponentVersion.version_no.desc())
        return query.all()
    except Exception:
        raise


def get_latest_version(item_component_id):
    try:
        query = db.session.query(ItemComponentVersion).filter(
            ItemComponentVersion.item_component_id == item_component_id
        ).order_by(ItemComponentVersion.version_no.desc())
        return query.first()
    except Exception:
        raise


def get_max_version_no(item_component_id):
    """Source of truth for the next version number — never trust the in-memory
    ItemComponent.doc_version alone, it can drift if a save half-failed."""
    try:
        query = db.session.query(func.max(ItemComponentVersion.version_no)).filter(
            ItemComponentVersion.item_component_id == item_component_id
        )
        return query.scalar() or 0
    except Exception:
        raise


def get_latest_versions_for_work_order(work_order_id):
    """Newest version row per ItemComponent of a WorkOrder. Used when a WorkRun
    starts and has to pin the whole document set at once."""
    try:
        latest = (
            db.session.query(
                ItemComponentVersion.item_component_id.label("item_component_id"),
                func.max(ItemComponentVersion.version_no).label("version_no"),
            )
            .join(ItemComponent, ItemComponent.item_component_id == ItemComponentVersion.item_component_id)
            .filter(ItemComponent.work_order_id == work_order_id)
            .group_by(ItemComponentVersion.item_component_id)
            .subquery()
        )
        query = db.session.query(ItemComponentVersion).join(
            latest,
            db.and_(
                ItemComponentVersion.item_component_id == latest.c.item_component_id,
                ItemComponentVersion.version_no == latest.c.version_no,
            ),
        )
        return query.all()
    except Exception:
        raise
