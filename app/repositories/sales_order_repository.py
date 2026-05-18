from app.con_sqlalchemy import Branch, SalesOrder, SalesItem, WorkOrder, WorkRun, TestResult, TestResultStatus, QCWorkOrder, QCCertification, QCCheckItem, MaterialList, ItemComponent, ComponentMaterialUsage, PickingRequest
from app.app import db
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import selectinload

from app.exception import NotFoundError, ValidationError


def search_sales_order(page, limit, search, branch_id=None):
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

        if branch_id is not None:
            query = query.filter(SalesOrder.branch_id == branch_id)

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}

    except Exception:
        raise

def assign_branch(doc_entry, branch_id):
    query = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry)
    sales_order = query.first()
    if not sales_order:
        raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
    old_branch_id = sales_order.branch_id
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

    return sales_order, old_branch_id


def get_all_sales_orders(page, limit, search, branch_id=None, start_date=None, end_date=None):
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

        produce_total_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry, SalesItem.produce == True)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        produce_has_workorder_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(
                SalesItem.doc_entry == SalesOrder.doc_entry,
                SalesItem.produce == True,
                db.session.query(WorkOrder)
                    .filter(WorkOrder.sales_item_id == SalesItem.sales_item_id)
                    .correlate(SalesItem)
                    .exists()
            )
            .correlate(SalesOrder)
            .scalar_subquery()
        )
        
        test_total_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(SalesItem.doc_entry == SalesOrder.doc_entry, SalesItem.test == True)
            .correlate(SalesOrder)
            .scalar_subquery()
        )

        test_has_qcworkorder_subq = (
            db.session.query(func.count(SalesItem.sales_item_id))
            .filter(
                SalesItem.doc_entry == SalesOrder.doc_entry,
                SalesItem.test == True,
                db.session.query(QCWorkOrder)
                    .filter(QCWorkOrder.sales_item_id == SalesItem.sales_item_id)
                    .correlate(SalesItem)
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
            produce_total_subq.label("produce_total"),
            produce_has_workorder_subq.label("produce_has_workorder"),
            test_total_subq.label("test_total"),
            test_has_qcworkorder_subq.label("test_has_qcworkorder"),
            Branch
        ).outerjoin(Branch, Branch.branch_id == SalesOrder.branch_id)

        if branch_id is not None:
            query = query.filter(SalesOrder.branch_id == branch_id)

        if search:
            query = query.filter(
                or_(
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                )
            )

        if start_date is not None:
            query = query.filter(SalesOrder.created_date >= start_date)
        if end_date is not None:
            query = query.filter(SalesOrder.created_date <= end_date)

        query = query.order_by(SalesOrder.created_date.desc())
        return query.paginate(page=page, per_page=limit, error_out=False)
    except Exception:
        raise


def get_sales_order_by_doc_entry(doc_entry):
    query = db.session.query(SalesOrder).filter(SalesOrder.doc_entry == doc_entry)
    sales_order = query.first()
    if not sales_order:
        raise NotFoundError(f"ไม่พบ SalesOrder : {doc_entry}")
    return sales_order


def get_sales_order_by_doc_num(doc_num, branch_id=None):
    query = db.session.query(SalesOrder).filter(SalesOrder.doc_num == doc_num)
    if branch_id is not None:
        query = query.filter(SalesOrder.branch_id == branch_id)
    sales_order = query.first()
    if not sales_order:
        raise NotFoundError(f"ไม่พบ SalesOrder doc_num : {doc_num}")
    return sales_order


def delete_sales_order_cascade(sales_order: SalesOrder):
    """
    Explicit cascade delete. SalesItem.doc_entry FK lacks ON DELETE CASCADE,
    so we must trigger child deletes manually. Order matters:
    TestResults first (SET NULL link to QCWorkOrder leaves orphans otherwise),
    then SalesItems (DB cascades MaterialList, WorkOrder->WorkRun->..., QCWorkOrder->...),
    then PickingRequest (doc_entry FK is SET NULL),
    then SalesOrder (cascades QCCertification).
    """
    doc_entry = sales_order.doc_entry

    sales_item_id_rows = db.session.query(SalesItem.sales_item_id).filter(
        SalesItem.doc_entry == doc_entry
    ).all()
    sales_item_ids = [r[0] for r in sales_item_id_rows]

    if sales_item_ids:
        qc_wo_id_rows = db.session.query(QCWorkOrder.qc_work_order_id).filter(
            QCWorkOrder.sales_item_id.in_(sales_item_ids)
        ).all()
        qc_wo_ids = [r[0] for r in qc_wo_id_rows]

        if qc_wo_ids:
            test_result_id_rows = db.session.query(TestResult.test_result_id).filter(
                TestResult.qc_work_order_id.in_(qc_wo_ids)
            ).all()
            test_result_ids = [r[0] for r in test_result_id_rows]
            if test_result_ids:
                db.session.query(TestResult).filter(
                    TestResult.test_result_id.in_(test_result_ids)
                ).delete(synchronize_session=False)

        db.session.query(SalesItem).filter(
            SalesItem.doc_entry == doc_entry
        ).delete(synchronize_session=False)

    db.session.query(PickingRequest).filter(
        PickingRequest.doc_entry == doc_entry
    ).delete(synchronize_session=False)

    db.session.delete(sales_order)


def get_sales_order_detail(doc_entry, branch_id=None):
    try:
        query = (
            db.session.query(SalesOrder, Branch)
            .options(
                selectinload(SalesOrder.sales_items).options(
                    selectinload(SalesItem.material_list),
                    selectinload(SalesItem.work_order),
                ),
                selectinload(SalesOrder.certifications)
                    .selectinload(QCCertification.check_items),
            )
            .outerjoin(Branch, Branch.branch_id == SalesOrder.branch_id)
            .filter(SalesOrder.doc_entry == doc_entry)
        )

        if branch_id is not None:
            query = query.filter(SalesOrder.branch_id == branch_id)

        sales_order = query.first()
        if not sales_order:
            raise NotFoundError(f"ไม่พบใบ Sales Order นี้ -> {doc_entry}")
        return sales_order
    except Exception:
        raise
    


