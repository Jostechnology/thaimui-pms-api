from app.con_sqlalchemy import (
    WorkOrder, WorkOrderStatus, WorkRun, SalesOrder, SalesItem,
    WorkPhase, WorkPhaseBreak, WorkAssignment, Employee,
    ItemComponent, ComponentMaterialUsage, MaterialList,
    TestResult,
)
from app.app import db
from sqlalchemy import desc, extract, or_
from sqlalchemy.orm import selectinload
from flask import g


def _work_order_options():
    """Eager-load exactly what WorkOrderSchemaDetail needs — nothing more."""
    return [
        selectinload(WorkOrder.sales_item),
        selectinload(WorkOrder.work_runs),
        selectinload(WorkOrder.item_components)
            .selectinload(ItemComponent.material_usages)
            .selectinload(ComponentMaterialUsage.material_list),
    ]


def get_all_work_orders(page, limit, search, filter, month):
    try:
        query = db.session.query(WorkOrder).options(selectinload(WorkOrder.sales_item))
        branch_id = g.get("branch_id")
        if branch_id:
            query = query.filter(WorkOrder.branch_id == branch_id)
        if search:
            query = query.filter(
                db.or_(
                    WorkOrder.doc_num.ilike(f"%{search}%"),
                    WorkOrder.work_order_code.ilike(f"%{search}%"),
                )
            )
        if filter:
            query = query.filter(WorkOrder.status == filter)
        if month:
            filter_year, filter_month = map(int, month.split('-'))
            query = query.filter(
                extract('year', WorkOrder.created_date) == filter_year,
                extract('month', WorkOrder.created_date) == filter_month
            )
        query = query.order_by(desc(WorkOrder.created_date))
        query = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": query.items, "total": query.total, "page": query.page, "pages": query.pages}
    except Exception:
        raise

def get_work_order_by_id(work_order_id):
    try:
        work_order = (
            db.session.query(WorkOrder)
            .options(*_work_order_options())
            .filter(WorkOrder.work_order_id == work_order_id)
            .first()
        )
        return work_order
    except Exception:
        raise

def get_work_order_by_center_sales_item_id(center_sales_item_id):
    try:
        work_order = (
            db.session.query(WorkOrder)
            .join(WorkOrder.sales_item)
            .options(*_work_order_options())
            .filter(SalesItem.center_sales_item_id == center_sales_item_id)
            .first()
        )
        return work_order
    except Exception:
        raise

