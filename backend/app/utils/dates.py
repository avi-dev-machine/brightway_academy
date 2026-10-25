"""Date helpers. Business dates (due dates, attendance) use the academy's local timezone."""

import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo


def add_months(start: date, months: int) -> date:
    """Add calendar months, clamping the day to the end of the target month."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def local_now(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))


def local_today(timezone: str) -> date:
    return local_now(timezone).date()
