from sqlalchemy import extract

from app.con_sqlalchemy import OperationCostMonthly
from app.app import db

def get_all_operation_cost_monthly(page, per_page, search, month):
    try:
        query = OperationCostMonthly.query
        if search:
            query = query.filter(OperationCostMonthly.operation_cost_date.contains(search))
        if month:
            filter_year, filter_month = map(int, month.split('-'))
            query = query.filter(
                extract('year', OperationCostMonthly.operation_cost_date) == filter_year,
                extract('month', OperationCostMonthly.operation_cost_date) == filter_month
            )
        query = query.paginate(page=page, per_page=per_page, error_out=False)
        return {"items": query.items, "total_pages": query.pages}
    except Exception:
        raise

def get_operation_cost_monthly_by_id(operation_cost_monthly_id):
    try:
        operation_cost_monthly = OperationCostMonthly.query.get(operation_cost_monthly_id)
        return operation_cost_monthly
    except Exception:
        raise