from app.con_sqlalchemy import MaterialList
from app.app import db


def get_all_material_lists(page, limit, search):
    try:
        query = MaterialList.query
        if search:
            query = query.filter(
                db.or_(
                    MaterialList.item_code.ilike(f"%{search}%"),
                    MaterialList.item_name.ilike(f"%{search}%"),
                )
            )
        query = query.order_by(MaterialList.created_date.desc())
        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total_pages": result.pages}
    except Exception:
        raise


def create_material_list(material):
    try:
        db.session.add(material)
        db.session.flush()
        return material
    except Exception:
        db.session.rollback()
        raise
