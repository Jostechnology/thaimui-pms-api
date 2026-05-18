"""Labor cost calculator. Splits per-assignment time into base/day/ot using shift + holiday config."""
from datetime import datetime, date, time, timedelta
from app.con_sqlalchemy import Shift, EmployeeShift
from app.repositories import shift_repository, employee_shift_repository, holiday_repository
from app.repositories import employee_salary_repository


_DAY_TOKENS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _to_naive(dt):
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _parse_work_days(csv):
    if not csv:
        return set()
    return {t.strip().upper() for t in csv.split(",") if t.strip()}


def _get_shift_for_employee(employee_id, default_shift):
    """Return (start_time, end_time, work_days_set, shift_multipliers). Override only changes window/days."""
    override = employee_shift_repository.get_by_employee(employee_id) if employee_id else None
    if override:
        return (
            override.start_time or default_shift.start_time,
            override.end_time or default_shift.end_time,
            _parse_work_days(override.work_days) or _parse_work_days(default_shift.work_days),
        )
    return (
        default_shift.start_time,
        default_shift.end_time,
        _parse_work_days(default_shift.work_days),
    )


def _overlap_seconds(a_start, a_end, b_start, b_end):
    if a_end <= b_start or b_end <= a_start:
        return 0.0
    return (min(a_end, b_end) - max(a_start, b_start)).total_seconds()


def _slice_by_day(slot_start, slot_end):
    """Yield (day_date, day_slot_start, day_slot_end) per calendar day overlapped by slot."""
    if slot_end <= slot_start:
        return
    cursor = slot_start
    while cursor < slot_end:
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time(0, 0))
        seg_end = min(next_midnight, slot_end)
        yield cursor.date(), cursor, seg_end
        cursor = seg_end


def _subtract_breaks(slot_start, slot_end, breaks):
    """Return list of (start, end) intervals after subtracting break overlaps."""
    intervals = [(slot_start, slot_end)]
    for b in breaks:
        if not b.break_start:
            continue
        b_start = _to_naive(b.break_start)
        b_end = _to_naive(b.break_end) if b.break_end else slot_end
        if b_end <= b_start:
            continue
        new_intervals = []
        for s, e in intervals:
            if b_end <= s or b_start >= e:
                new_intervals.append((s, e))
                continue
            if b_start > s:
                new_intervals.append((s, b_start))
            if b_end < e:
                new_intervals.append((b_end, e))
        intervals = new_intervals
        if not intervals:
            return []
    return intervals


def calc_assignment_labor(assignment, employee, breaks, run_anchor_date, default_shift, holiday_dates):
    """Compute base/day/ot labor cost for a single assignment.

    Args:
        assignment: object with from_time, to_time
        employee: Employee model with base_salary, day_rate, ot_hourly_rate
        breaks: iterable of break rows with break_start, break_end
        run_anchor_date: datetime used to look up historic pay rates (e.g. work_run.created_date)
        default_shift: Shift row (global default)
        holiday_dates: set[date] of active holidays in the relevant range

    Returns dict: {base_cost, day_cost, ot_cost, effective_seconds, hourly breakdown ...}
    """
    if not assignment.from_time:
        return _empty_breakdown()

    a_start = _to_naive(assignment.from_time)
    a_end = _to_naive(assignment.to_time) if assignment.to_time else _to_naive(datetime.now())
    if a_end <= a_start:
        return _empty_breakdown()

    historic = employee_salary_repository.get_salary_at_date(employee.employee_id, run_anchor_date) if employee else None
    if historic is not None:
        base_salary, day_rate, ot_hourly = historic
    else:
        base_salary = (employee.base_salary or 0.0) if employee else 0.0
        day_rate = (employee.day_rate or 0.0) if employee else 0.0
        ot_hourly = (employee.ot_hourly_rate or 0.0) if employee else 0.0

    start_time, end_time, work_days = _get_shift_for_employee(employee.employee_id if employee else None, default_shift)
    ot_mult = default_shift.ot_multiplier or 1.0
    weekend_mult = default_shift.weekend_multiplier or 1.0
    holiday_mult = default_shift.holiday_multiplier or 1.0

    base_per_sec = (base_salary / 30.0 / 8.0 / 3600.0) if base_salary > 0 else 0.0
    day_per_sec = (day_rate / 8.0 / 3600.0) if day_rate > 0 else 0.0
    ot_per_sec_weekday = (ot_hourly * ot_mult) / 3600.0 if ot_hourly > 0 else 0.0
    ot_per_sec_weekend = (ot_hourly * weekend_mult) / 3600.0 if ot_hourly > 0 else 0.0
    ot_per_sec_holiday = (ot_hourly * holiday_mult) / 3600.0 if ot_hourly > 0 else 0.0

    base_cost = 0.0
    day_cost = 0.0
    ot_cost = 0.0
    eff_secs_total = 0.0

    for day_date, day_slot_start, day_slot_end in _slice_by_day(a_start, a_end):
        eff_intervals = _subtract_breaks(day_slot_start, day_slot_end, breaks)
        if not eff_intervals:
            continue

        is_holiday = day_date in holiday_dates
        is_workday = _DAY_TOKENS[day_date.weekday()] in work_days
        regular_window_start = datetime.combine(day_date, start_time) if start_time else None
        regular_window_end = datetime.combine(day_date, end_time) if end_time else None

        for s, e in eff_intervals:
            secs = (e - s).total_seconds()
            if secs <= 0:
                continue
            eff_secs_total += secs
            base_cost += base_per_sec * secs

            if is_holiday:
                ot_cost += ot_per_sec_holiday * secs
            elif not is_workday:
                ot_cost += ot_per_sec_weekend * secs
            else:
                regular_secs = _overlap_seconds(s, e, regular_window_start, regular_window_end) if regular_window_start else 0.0
                ot_secs = max(0.0, secs - regular_secs)
                day_cost += day_per_sec * regular_secs
                ot_cost += ot_per_sec_weekday * ot_secs

    return {
        "base_cost": round(base_cost, 6),
        "day_cost": round(day_cost, 6),
        "ot_cost": round(ot_cost, 6),
        "effective_seconds": round(eff_secs_total, 2),
        "base_salary_at_run": base_salary,
        "day_rate_at_run": day_rate,
        "ot_hourly_rate_at_run": ot_hourly,
    }


def _empty_breakdown():
    return {
        "base_cost": 0.0,
        "day_cost": 0.0,
        "ot_cost": 0.0,
        "effective_seconds": 0.0,
        "base_salary_at_run": 0.0,
        "day_rate_at_run": 0.0,
        "ot_hourly_rate_at_run": 0.0,
    }


def get_default_shift_or_fallback():
    """Return the configured default Shift. If none exists, return a transient 8-5 Mon-Fri fallback."""
    shift = shift_repository.get_default_shift()
    if shift:
        return shift
    return Shift(
        name="FALLBACK",
        start_time=time(8, 0),
        end_time=time(17, 0),
        work_days="MON,TUE,WED,THU,FRI",
        ot_multiplier=1.5,
        weekend_multiplier=2.0,
        holiday_multiplier=3.0,
        is_default=False,
    )


def get_active_holiday_dates_for_assignments(assignments):
    """Compute the min/max date span across assignments and load active holidays in that range."""
    naive = [(_to_naive(a.from_time), _to_naive(a.to_time)) for a in assignments if a.from_time]
    if not naive:
        return set()
    starts = [s for s, _ in naive if s]
    ends = [e if e else s for s, e in naive]
    if not starts:
        return set()
    min_d = min(starts).date()
    max_d = max(ends).date() if ends else min_d
    return holiday_repository.get_active_dates_in_range(min_d, max_d)


def aggregate_labor_costs(assignments, breaks, run_anchor_date):
    """Aggregate per-assignment base/day/ot into totals and per-employee rows.

    Returns dict: {totals: {base, day, ot, total}, rows: [...]}.
    """
    default_shift = get_default_shift_or_fallback()
    holiday_dates = get_active_holiday_dates_for_assignments(assignments)

    total_base = 0.0
    total_day = 0.0
    total_ot = 0.0
    rows = []

    for a in assignments:
        emp = a.employee
        breakdown = calc_assignment_labor(a, emp, breaks, run_anchor_date, default_shift, holiday_dates)
        total_base += breakdown["base_cost"]
        total_day += breakdown["day_cost"]
        total_ot += breakdown["ot_cost"]
        rows.append({"assignment": a, **breakdown})

    return {
        "totals": {
            "base_cost": round(total_base, 6),
            "day_cost": round(total_day, 6),
            "ot_cost": round(total_ot, 6),
            "total": round(total_base + total_day + total_ot, 6),
        },
        "rows": rows,
    }
