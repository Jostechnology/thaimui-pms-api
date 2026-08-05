from sqlalchemy.orm import selectinload

from app.app import db
from app.con_sqlalchemy import TestSpec, TestSpecSourceType


def get_test_spec_by_id(test_spec_id):
    """Detail: TestSpec + item_component + item_component_version + qc_work_orders
    (one layer each, per the Data Retrieval Handling convention)."""
    try:
        query = db.session.query(TestSpec).options(
            selectinload(TestSpec.item_component),
            selectinload(TestSpec.item_component_version),
            selectinload(TestSpec.qc_work_orders),
        ).filter(TestSpec.test_spec_id == test_spec_id)
        return query.first()
    except Exception:
        raise


def get_test_specs_by_sales_item(sales_item_id):
    """Lightweight: every TestSpec for a SalesItem, no eager loading. Used for
    write-side reconciliation (qc_work_order_service.sync_component_test_specs
    and the create_qc_work_order planned-qty guard), which only needs the
    plain columns (source_type, item_component_id, section_keys, ...)."""
    try:
        query = db.session.query(TestSpec).filter(
            TestSpec.sales_item_id == sales_item_id
        )
        return query.all()
    except Exception:
        raise


def get_component_section_spec(sales_item_id, item_component_id):
    """The one COMPONENT_SECTION TestSpec for (sales_item, item_component) —
    unique per uq_test_spec_sales_item_component."""
    try:
        query = db.session.query(TestSpec).filter(
            TestSpec.sales_item_id == sales_item_id,
            TestSpec.item_component_id == item_component_id,
            TestSpec.source_type == TestSpecSourceType.COMPONENT_SECTION,
        )
        return query.first()
    except Exception:
        raise


def create_test_spec(test_spec):
    try:
        db.session.add(test_spec)
        return test_spec
    except Exception:
        raise


def delete_test_spec(test_spec):
    try:
        db.session.delete(test_spec)
        return test_spec
    except Exception:
        raise
