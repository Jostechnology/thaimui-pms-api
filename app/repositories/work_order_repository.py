from app.con_sqlalchemy import (
    WorkOrder, WorkOrderStatus, WorkRun, SalesOrder, SalesItem,
    WorkPhase, WorkPhaseBreak, WorkAssignment, Employee,
    ItemComponent, ComponentMaterialUsage, MaterialList,
    ComponentSpec, ComponentSpecType, ComponentOption, ComponentOptionType,
    TestResult,
)
from app.app import db
from sqlalchemy import extract, or_
from sqlalchemy.orm import selectinload


def _work_order_options():
    """Eager-load exactly what WorkOrderSchemaDetail needs — nothing more."""
    return [
        selectinload(WorkOrder.sales_item),
        selectinload(WorkOrder.work_runs),
        selectinload(WorkOrder.item_components)
            .selectinload(ItemComponent.material_usages)
            .selectinload(ComponentMaterialUsage.material_list),
        selectinload(WorkOrder.item_components)
            .selectinload(ItemComponent.component_specs)
            .selectinload(ComponentSpec.component_spec_type),
        selectinload(WorkOrder.item_components)
            .selectinload(ItemComponent.component_options)
            .selectinload(ComponentOption.component_option_type),
    ]


def get_all_work_orders(page, limit, search, filter, month):
    try:
        query = db.session.query(WorkOrder).options(selectinload(WorkOrder.sales_item))
        if search:
            query = query.filter(WorkOrder.doc_num.ilike(f"%{search}%"))
        if filter:
            query = query.filter(WorkOrder.status == filter)
        if month:
            filter_year, filter_month = map(int, month.split('-'))
            query = query.filter(
                extract('year', WorkOrder.created_date) == filter_year,
                extract('month', WorkOrder.created_date) == filter_month
            )
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

