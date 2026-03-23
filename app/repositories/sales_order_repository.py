from app.con_sqlalchemy import SalesOrder, SalesItem, WorkOrder, WorkRun, TestResult, TestResultStatus, QCWorkOrder, QCCertification, QCCheckItem, MaterialList
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
        )

        result = query.paginate(page=page, per_page=limit, error_out=False)
        return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}

    except Exception:
        raise

def get_all_sales_orders(page, limit, search):
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
        ).order_by(desc(SalesOrder.created_date))

        if search:
            query = query.filter(
                or_(
                    SalesOrder.doc_num.ilike(f"%{search}%"),
                    SalesOrder.card_name.ilike(f"%{search}%"),
                    SalesOrder.card_code.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(SalesOrder.doc_num.desc())
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

