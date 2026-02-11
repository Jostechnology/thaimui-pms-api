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


def create_material_list(data):
    try:
        material = MaterialList(
            sales_item_id=data.get("sales_item_id"),
            item_code=data.get("item_code"),
            item_name=data.get("item_name"),
            item_description=data.get("item_description"),
            item_num=data.get("item_num"),
            cost_price=data.get("cost_price"),
            unit_price=data.get("unit_price"),
        )
        db.session.add(material)
        db.session.commit()
        return material
    except Exception:
        db.session.rollback()
        raise
