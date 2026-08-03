from app.con_sqlalchemy import (
    WorkOrder, WorkOrderStatus, WorkRun, SalesOrder, SalesItem,
    ItemComponent, ComponentMaterialUsage, MaterialList,
    TestResult,
)
from app.app import db
from sqlalchemy import desc, extract, or_
from sqlalchemy.orm import selectinload
from flask import g


def _work_order_options():
    """Eager-load exactly what WorkOrderSchemaDetail needs — nothing more.

    sales_item.material_list is included here (not on the lighter
    get_all_work_orders options) because WorkOrderSchemaDetail dumps
    sales_item via SalesItemSchemaDetail, which carries material_list. A
    WorkOrder maps to exactly one SalesItem (SalesItem.work_order is
    uselist=False), so this is one selectinload of a bounded, per-order-line
    row set — not a list-endpoint-scale cost. Without this, material_list
    is either omitted or lazily selected outside the repository the moment
    something touches sales_item.material_list, which is exactly what this
    project's lazy policy forbids.
    """
    return [
        selectinload(WorkOrder.sales_item).selectinload(SalesItem.material_list),
        selectinload(WorkOrder.work_runs),
        selectinload(WorkOrder.item_components)
            .selectinload(ItemComponent.material_usages)
            .selectinload(ComponentMaterialUsage.material_list),
        # component_template(+sections) so item_component_service.decorate_work_order_components
        # can resolve has_test_section/test_section_keys on each nested component
        # without lazy-loading.
        selectinload(WorkOrder.item_components).selectinload(ItemComponent.component_template),
        selectinload(WorkOrder.item_components).selectinload(ItemComponent.component_template_sections),
    ]


def get_all_work_orders(page, limit, search, filter, month, start_date=None, end_date=None):
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
        if start_date is not None:
            query = query.filter(WorkOrder.created_date >= start_date)
        if end_date is not None:
            query = query.filter(WorkOrder.created_date <= end_date)
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

def get_work_order_light(work_order_id):
    """No eager loading — for writes that only need the WorkOrder's own columns."""
    try:
        query = db.session.query(WorkOrder).filter(WorkOrder.work_order_id == work_order_id)
        return query.first()
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

