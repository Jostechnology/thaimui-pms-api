from app.ma_sqlalchemy import EmployeeSchema
from app.repositories import employee_repository


def get_all_employees(data):
    try:
        page = data.get("page", 1)
        limit = data.get("limit", 10)
        search = data.get("search", "")
        result = employee_repository.get_all_employees(page, limit, search)
        return {"items": EmployeeSchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise
