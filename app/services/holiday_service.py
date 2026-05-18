from datetime import date, datetime
import re
import requests
from app.app import db
from app.con_sqlalchemy import Holiday
from app.exception import NotFoundError, ValidationError, OuterServicesError
from app.repositories import holiday_repository


# MyHora.com is Thailand-specific; date.nager.at does not cover TH (returns 204).
# ICS endpoint is cleanest — JSON variant is malformed (missing commas between events).
_MYHORA_ICS_URL = "https://www.myhora.com/calendar/ical/holiday.aspx?{year}.ics"


def _parse_ics_events(ics_text: str):
    """Yield {'date': date, 'name': str} per VEVENT block."""
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, flags=re.DOTALL)
    for block in blocks:
        m_date = re.search(r"DTSTART;VALUE=DATE:(\d{8})", block)
        m_summary = re.search(r"SUMMARY:(.+)", block)
        if not m_date or not m_summary:
            continue
        ymd = m_date.group(1)
        try:
            d = datetime.strptime(ymd, "%Y%m%d").date()
        except ValueError:
            continue
        name = m_summary.group(1).strip().rstrip("\r")
        if not name:
            continue
        yield {"date": d, "name": name}


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except Exception:
            raise ValidationError(f"Invalid date: {value}")
    raise ValidationError(f"Invalid date: {value}")


def get_all_holidays(data):
    search = data.get("search", "")
    year = data.get("year")
    page = data.get("page", 1)
    per_page = data.get("per_page", 31)
    return holiday_repository.get_all_holidays(search, year, page, per_page)


def get_holiday_by_id(holiday_id):
    holiday = holiday_repository.get_holiday_by_id(holiday_id)
    if not holiday:
        raise NotFoundError(f"Holiday id {holiday_id} not found")
    return holiday


def create_holiday(data):
    try:
        holiday_date = _parse_date(data.get("holiday_date"))
        if not holiday_date:
            raise ValidationError("holiday_date is required")
        existing = holiday_repository.get_holiday_by_date(holiday_date)
        if existing:
            raise ValidationError(f"Holiday already exists on {holiday_date.isoformat()}")
        holiday = Holiday(
            holiday_date=holiday_date,
            name=data.get("name") or holiday_date.isoformat(),
            is_active=bool(data.get("is_active", True)),
            source=data.get("source", "MANUAL"),
        )
        holiday_repository.create_holiday(holiday)
        db.session.commit()
        return holiday
    except Exception:
        db.session.rollback()
        raise


def update_holiday(holiday_id, data):
    try:
        holiday = get_holiday_by_id(holiday_id)
        if "holiday_date" in data:
            holiday.holiday_date = _parse_date(data["holiday_date"])
        if "name" in data:
            holiday.name = data["name"]
        if "is_active" in data:
            holiday.is_active = bool(data["is_active"])
        if "source" in data:
            holiday.source = data["source"]
        db.session.commit()
        return holiday
    except Exception:
        db.session.rollback()
        raise


def delete_holiday(holiday_id):
    try:
        holiday = get_holiday_by_id(holiday_id)
        holiday_repository.delete_holiday(holiday)
        db.session.commit()
        return {"message": f"Deleted holiday id {holiday_id}"}
    except Exception:
        db.session.rollback()
        raise


def sync_holidays_from_api(year):
    """Pull Thai public holidays for the given year from MyHora and upsert.
    Existing rows keep their is_active value. New rows default to is_active=True.
    """
    try:
        if not year:
            raise ValidationError("year is required")
        url = _MYHORA_ICS_URL.format(year=int(year))
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (thaimui-api holiday sync)"},
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            raise OuterServicesError(f"Holiday source returned HTTP {resp.status_code}")
        if not resp.text or "BEGIN:VEVENT" not in resp.text:
            raise OuterServicesError(f"Holiday source returned no events for year {year}")
        events = list(_parse_ics_events(resp.text))
    except (ValidationError, OuterServicesError):
        raise
    except Exception as e:
        raise OuterServicesError(f"Failed to fetch holidays: {e}")

    inserted = 0
    skipped = 0
    try:
        for ev in events:
            d = ev["date"]
            if d.year != int(year):
                continue
            existing = holiday_repository.get_holiday_by_date(d)
            if existing:
                skipped += 1
                continue
            h = Holiday(holiday_date=d, name=ev["name"], is_active=True, source="API")
            holiday_repository.create_holiday(h)
            inserted += 1
        db.session.commit()
        return {"inserted": inserted, "skipped_existing": skipped, "year": int(year)}
    except Exception:
        db.session.rollback()
        raise
