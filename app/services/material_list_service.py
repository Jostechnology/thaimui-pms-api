from app.con_sqlalchemy import MaterialList
from app.repositories import material_list_repository
from app.services import transaction_service
from app.app import db


def get_all_material_lists(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        result = material_list_repository.get_all_material_lists(page, per_page, search)
        return {"items": result["items"], "total": result["total"], "page": result["page"], "pages": result["pages"]}
    except Exception:
        raise


def create_material_list(data):
    try:
        material = MaterialList(
            sales_item_id=data.get("sales_item_id"),
            item_code=data.get("item_code"),
            item_name=data.get("item_name"),
            item_description=data.get("item_description"),
            quantity=data.get("quantity"),
            unit_name=data.get("unit_name", "Piece"),
            unit_id=data.get("unit_id", 0),
            cost_price=data.get("cost_price"),
            unit_price=data.get("unit_price"),
        )
        material = material_list_repository.create_material_list(material)
        transaction_service.create_init_material_transaction(material, "INIT")
        db.session.commit()
        return material
    except Exception:
        raise
