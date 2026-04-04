from app.con_sqlalchemy import SalesOrder, SalesItem, WorkOrder, WorkRun, TestResult, TestResultStatus, QCWorkOrder, QCCertification, QCCheckItem, MaterialList, ItemComponent, ComponentMaterialUsage
from app.app import db
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import selectinload

from app.exception import NotFoundError


def search_sales_order(page, limit, search):
    try:
        query = (
            db.session.query(SalesOrder.doc_entry, SalesOrder.doc_num)
            .filter(
                or_(
                    SalesOrder.doc_entry.ilike(f"%{search}%"),
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.slp_code.ilike(f"%{search}%"),
                    SalesOrder.slp_name.ilike(f"%{search}%"),
                    SalesOrder.bpl_code.ilike(f"%{search}%"),
                    SalesOrder.bpl_name.ilike(f"%{search}%"),
                    SalesOrder.group_code.ilike(f"%{search}%"),
                    SalesOrder.group_name.ilike(f"%{search}%"),
                    SalesOrder.po_number.ilike(f"%{search}%"),
                )
            )
            .distinct()
            .order_by(desc(SalesOrder.created_date))
        )

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}

    except Exception:
        raise

def assign_branch(doc_entry, branch_id):
    query = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry)
    sales_order = query.first()
    if not sales_order:
        raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
    sales_order.branch_id = branch_id

    # Cascade to SalesItem
    db.session.query(SalesItem).filter(
        SalesItem.doc_entry == doc_entry
    ).update({SalesItem.branch_id: branch_id}, synchronize_session=False)

    # Get sales_item_ids for this order to reach MaterialList
    sales_item_ids = [
        row[0] for row in
        db.session.query(SalesItem.sales_item_id).filter(SalesItem.doc_entry == doc_entry)
    ]
    if sales_item_ids:
        db.session.query(MaterialList).filter(
            MaterialList.sales_item_id.in_(sales_item_ids)
        ).update({MaterialList.branch_id: branch_id}, synchronize_session=False)

    # Cascade to QCWorkOrder (via sales_item_ids already fetched)
    if sales_item_ids:
        db.session.query(QCWorkOrder).filter(
            QCWorkOrder.sales_item_id.in_(sales_item_ids)
        ).update({QCWorkOrder.branch_id: branch_id}, synchronize_session=False)

    # Cascade to WorkOrder
    db.session.query(WorkOrder).filter(
        WorkOrder.doc_entry == doc_entry
    ).update({WorkOrder.branch_id: branch_id}, synchronize_session=False)

    # Get work_order_ids to reach ItemComponent and ComponentMaterialUsage
    work_order_ids = [
        row[0] for row in
        db.session.query(WorkOrder.work_order_id).filter(WorkOrder.doc_entry == doc_entry)
    ]
    if work_order_ids:
        item_component_ids = [
            row[0] for row in
            db.session.query(ItemComponent.item_component_id).filter(
                ItemComponent.work_order_id.in_(work_order_ids)
            )
        ]
        db.session.query(ItemComponent).filter(
            ItemComponent.work_order_id.in_(work_order_ids)
        ).update({ItemComponent.branch_id: branch_id}, synchronize_session=False)

        if item_component_ids:
            db.session.query(ComponentMaterialUsage).filter(
                ComponentMaterialUsage.item_component_id.in_(item_component_ids)
            ).update({ComponentMaterialUsage.branch_id: branch_id}, synchronize_session=False)

    return sales_order


def get_all_sales_orders(page, limit, search, show_unassigned=False, branch_id=None):
    try:
        items_total_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        quantity_to_produce_subq = (
            db.session.query(func.coalesce(func.sum(WorkOrder.quantity), 0))
            .join(SalesItem, WorkOrder.sales_item_id == SalesItem.sales_item_id)
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        produced_qty_subq = (
            db.session.query(func.coalesce(func.sum(WorkRun.usable_qty), 0))
            .join(WorkOrder, WorkRun.work_order_id == WorkOrder.work_order_id)
            .join(SalesItem, WorkOrder.sales_item_id == SalesItem.sales_item_id)
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        qc_count_subq = (
            db.session.query(func.count(QCWorkOrder.qc_work_order_id))
            .join(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        qc_passed_subq = (
            db.session.query(func.count(QCWorkOrder.qc_work_order_id))
            .join(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
            .filter(
                SalesItem.doc_entry == SalesOrder.doc_entry,
                db.session.query(TestResult)
                    .filter(
                        TestResult.qc_work_order_id == QCWorkOrder.qc_work_order_id,
                        TestResult.overall_status == TestResultStatus.PASSED,
                    )
                    .correlate(QCWorkOrder)
                    .exists()
            )
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        qc_failed_subq = (
            db.session.query(func.count(QCWorkOrder.qc_work_order_id))
            .join(SalesItem, SalesItem.sales_item_id == QCWorkOrder.sales_item_id)
            .filter(
                SalesItem.doc_entry == SalesOrder.doc_entry,
                db.session.query(TestResult)
                    .filter(
                        TestResult.qc_work_order_id == QCWorkOrder.qc_work_order_id,
                        TestResult.overall_status == TestResultStatus.FAILED,
                    )
                    .correlate(QCWorkOrder)
                    .exists()
            )
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        query = db.session.query(
            SalesOrder,
            items_total_subq.label("items_total"),
            quantity_to_produce_subq.label("quantity_to_produce"),
            produced_qty_subq.label("produced_qty"),
            qc_count_subq.label("qc_count"),
            qc_passed_subq.label("qc_passed"),
            qc_failed_subq.label("qc_failed"),
        )

        if show_unassigned:
            query = query.filter(SalesOrder.branch_id.is_(None))
        elif branch_id is not None:
            query = query.filter(SalesOrder.branch_id == branch_id)

        if search:
            query = query.filter(
                or_(
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(SalesOrder.created_date.desc())
        return query.paginate(page=page, per_page=limit, error_out=False)
    except Exception:
        raise


def get_sales_order_by_doc_entry(doc_entry):
    query = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry)
    return query.first()


def get_sales_order_detail(doc_entry):
    try:
        sales_order = (
            db.session.query(SalesOrder)
            .options(
                selectinload(SalesOrder.sales_items)
                    .selectinload(SalesItem.material_list),
                selectinload(SalesOrder.certifications)
                    .selectinload(QCCertification.check_items),
            )
            .filter(SalesOrder.doc_entry == doc_entry)
            .first()
        )
        if not sales_order:
            raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
        return sales_order
    except Exception:
        raise

