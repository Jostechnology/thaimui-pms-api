from app.con_sqlalchemy import Holiday
from app.app import db
from sqlalchemy import extract


def get_all_holidays(search="", year=None, page=1, per_page=10):
    query = db.session.query(Holiday)
    if search:
        query = query.filter(Holiday.name.ilike(f"%{search}%"))
    if year:
        query = query.filter(extract('year', Holiday.holiday_date) == int(year))
    query = query.order_by(Holiday.holiday_date.asc())
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": result.items, "total": result.total, "page": result.page, "pages": result.pages}


def get_holiday_by_id(holiday_id):
    query = db.session.query(Holiday).filter(Holiday.holiday_id == holiday_id)
    return query.first()


def get_holiday_by_date(holiday_date):
    query = db.session.query(Holiday).filter(Holiday.holiday_date == holiday_date)
    return query.first()


def get_active_dates_in_range(start_date, end_date):
    query = db.session.query(Holiday.holiday_date).filter(
        Holiday.is_active == True,
        Holiday.holiday_date >= start_date,
        Holiday.holiday_date <= end_date,
    )
    return {row[0] for row in query.all()}


def create_holiday(holiday):
    db.session.add(holiday)
    return holiday


def delete_holiday(holiday):
    db.session.delete(holiday)
