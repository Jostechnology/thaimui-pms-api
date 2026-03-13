from app.con_sqlalchemy import OperationCostMonthly
from app.ma_sqlalchemy import OperationCostMonthlySchema
from app.repositories import operation_cost_monthly_repository
from app.app import db

def get_all_operation_cost_monthly(data):
    try:
        page = data.get("page", 1)
        per_page = data.get("per_page", 10)
        search = data.get("search", "")
        month = data.get("month", "")
        result = operation_cost_monthly_repository.get_all_operation_cost_monthly(page, per_page, search, month)
        return {"items": OperationCostMonthlySchema(many=True).dump(result["items"]), "total_pages": result["total_pages"]}
    except Exception:
        raise

def get_operation_cost_monthly_by_id(operation_cost_monthly_id):
    try:
        operation_cost_monthly = operation_cost_monthly_repository.get_operation_cost_monthly_by_id(operation_cost_monthly_id)
        if not operation_cost_monthly:
            raise Exception(f"Operation Cost Monthly id {operation_cost_monthly_id} not found")
        return OperationCostMonthlySchema().dump(operation_cost_monthly)
    except Exception:
        raise

def create_operation_cost_monthly(data):
    try:
        operation_cost_monthly = OperationCostMonthly(
            operation_cost_date=data.get("operation_cost_date"),
            depreciation_building_cost=data.get("depreciation_building_cost", 0),
            depreciation_building_period=data.get("depreciation_building_period", 0),
            depreciation_util_cost=data.get("depreciation_util_cost", 0),
            depreciation_util_period=data.get("depreciation_util_period", 0),
            office_rent_cost=data.get("office_rent_cost", 0),
            office_supplies_cost=data.get("office_supplies_cost", 0),
            water_cost=data.get("water_cost", 0),
            electricity_cost=data.get("electricity_cost", 0),
            utility_cost=data.get("utility_cost", 0)
        )
        db.session.add(operation_cost_monthly)
        db.session.commit()
        return OperationCostMonthlySchema().dump(operation_cost_monthly)
    except Exception:
        raise

def update_operation_cost_monthly(operation_cost_monthly_id, data):
    try:
        operation_cost_monthly = get_operation_cost_monthly_by_id(operation_cost_monthly_id)

        for key, value in data.items():
            if hasattr(operation_cost_monthly, key):
                setattr(operation_cost_monthly, key, value)
        
        db.session.add(operation_cost_monthly)
        db.session.commit()
        return OperationCostMonthlySchema().dump(operation_cost_monthly)
    except Exception:
        raise

def delete_operation_cost_monthly(operation_cost_monthly_id):
    try:
        operation_cost_monthly = get_operation_cost_monthly_by_id(operation_cost_monthly_id)
        
        db.session.delete(operation_cost_monthly)
        db.session.commit()
        return {"message": "Operation Cost Monthly deleted successfully"}
    except Exception:
        raise
