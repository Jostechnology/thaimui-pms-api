from app.con_sqlalchemy import ItemDecodeSegment, ItemReference
from app.app import db


def get_segment_values(category, segment, code):
    """All legend field/value rows for one (category, segment, code) triple."""
    try:
        query = db.session.query(ItemDecodeSegment).filter(
            ItemDecodeSegment.category == category,
            ItemDecodeSegment.segment == segment,
            ItemDecodeSegment.code == code,
        )
        return query.all()
    except Exception:
        raise


def get_category_segments(category):
    """Distinct (segment, field) pairs stored for one category. Drives decoding:
    positions are derived from the stored data, not hardcoded."""
    try:
        query = db.session.query(
            ItemDecodeSegment.segment, ItemDecodeSegment.field
        ).filter(
            ItemDecodeSegment.category == category
        ).distinct()
        return query.all()
    except Exception:
        raise


def get_reference(item_code):
    """Exact-match reference row for a raw item code, or None."""
    try:
        query = db.session.query(ItemReference).filter(
            ItemReference.item_no == item_code
        )
        return query.first()
    except Exception:
        raise


def replace_category_segments(category, rows):
    """Delete-then-insert every segment row for one category. Runs inside the
    caller's transaction (caller commits). `rows` is a list of dicts with keys
    category/segment/code/field/value. Bulk-inserted for speed. Returns count."""
    try:
        del_query = db.session.query(ItemDecodeSegment).filter(
            ItemDecodeSegment.category == category
        )
        del_query.delete(synchronize_session=False)
        if rows:
            db.session.bulk_insert_mappings(ItemDecodeSegment, rows)
        return len(rows)
    except Exception:
        raise


def replace_all_reference(rows):
    """Delete-then-insert the whole reference table. Runs inside the caller's
    transaction. `rows` is a list of dicts with keys item_no/item_description.
    Bulk-inserted for speed. Returns the inserted row count."""
    try:
        del_query = db.session.query(ItemReference)
        del_query.delete(synchronize_session=False)
        if rows:
            db.session.bulk_insert_mappings(ItemReference, rows)
        return len(rows)
    except Exception:
        raise
