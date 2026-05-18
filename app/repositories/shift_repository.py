from app.con_sqlalchemy import Shift
from app.app import db


def get_all_shifts(search="", page=1, per_page=10):
    query = db.session.query(Shift)
    if search:
        query = query.filter(Shift.name.ilike(f"%{search}%"))
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}


def get_shift_by_id(shift_id):
    query = db.session.query(Shift).filter(Shift.shift_id == shift_id)
    return query.first()


def get_default_shift():
    query = db.session.query(Shift).filter(Shift.is_default == True)
    return query.first()


def clear_default_flag():
    query = db.session.query(Shift).filter(Shift.is_default == True)
    for s in query.all():
        s.is_default = False


def create_shift(shift):
    db.session.add(shift)
    return shift
