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


def get_category_legend_rows(category):
    """All legend (segment, field, code, value) rows for one category, ordered
    for stable overview/export output. Drives both the overview endpoint and the
    workbook export — same source the decoder derives its (segment, field) pairs
    from."""
    try:
        query = db.session.query(
            ItemDecodeSegment.segment,
            ItemDecodeSegment.field,
            ItemDecodeSegment.code,
            ItemDecodeSegment.value,
        ).filter(
            ItemDecodeSegment.category == category
        ).order_by(
            ItemDecodeSegment.segment,
            ItemDecodeSegment.field,
            ItemDecodeSegment.code,
        )
        return query.all()
    except Exception:
        raise


def count_category_rows(category):
    """Total legend row count for one category (overview value_count)."""
    try:
        query = db.session.query(ItemDecodeSegment).filter(
            ItemDecodeSegment.category == category
        )
        return query.count()
    except Exception:
        raise


def get_reference_list(page, per_page, search):
    """Paginated reference rows. `search` (case-insensitive) matches item_no OR
    item_description. Ordered by item_no for stable paging."""
    try:
        query = db.session.query(ItemReference)
        if search:
            like = f"%{search}%"
            query = query.filter(
                (ItemReference.item_no.ilike(like)) |
                (ItemReference.item_description.ilike(like))
            )
        query = query.order_by(ItemReference.item_no)
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return result
    except Exception:
        raise


def count_reference():
    """Total reference row count (overview reference_count)."""
    try:
        query = db.session.query(ItemReference)
        return query.count()
    except Exception:
        raise


def get_all_reference_rows():
    """All reference rows ordered by item_no, for the export Reference sheet."""
    try:
        query = db.session.query(ItemReference).order_by(ItemReference.item_no)
        return query.all()
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
