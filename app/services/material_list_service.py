from app.con_sqlalchemy import MaterialList
from app.ma_sqlalchemy import MaterialListSchema
from app.repositories import material_list_repository


def get_all_material_lists(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = material_list_repository.get_all_material_lists(page, limit, search)
        return {"items": MaterialListSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
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
        material = material_list_repository.create_material_list(material)
        return MaterialListSchema().dump(material)
    except Exception:
        raise
