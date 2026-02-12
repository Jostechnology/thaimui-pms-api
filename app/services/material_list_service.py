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
        material = material_list_repository.create_material_list(data)
        return MaterialListSchema().dump(material)
    except Exception:
        raise
