from app.con_sqlalchemy import MaterialList, SalesItem
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
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}
    except Exception:
        raise


def create_material_list(material):
    db.session.add(material)
    return material

def get_material_list_of_items(item_ids : list[int]):
    try:
        query = db.session.query(MaterialList).filter(MaterialList.sales_item_id.in_(item_ids))
        materials = query.all()
        return materials
    except Exception:
        raise


def get_total_material_qty_by_code(doc_entry, item_code):
    """Sum MaterialList.quantity for a given item_code across all SalesItems in the SO."""
    query = (
        db.session.query(db.func.coalesce(db.func.sum(MaterialList.quantity), 0))
        .join(SalesItem, SalesItem.sales_item_id == MaterialList.sales_item_id)
        .filter(
            SalesItem.doc_entry == doc_entry,
            MaterialList.item_code == item_code,
        )
    )
    return query.scalar()
