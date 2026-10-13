"""Date helpers for the work journal module.

所有"今天是哪天""这周从周几开始"的判断都必须走这里，不能使用服务器操作系统时区，
也不能使用浏览器 toISOString().slice(0, 10)。时间戳统一存 UTC，日期按北京时间计算。
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc

WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def now_utc() -> datetime:
    """Return the current UTC time without tzinfo, matching the platform's DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_shanghai(moment: datetime) -> datetime:
    """Interpret a stored UTC timestamp in Beijing time."""
    aware = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment
    return aware.astimezone(SHANGHAI)


def today_shanghai() -> date:
    """Return the current work date in Beijing time."""
    return datetime.now(SHANGHAI).date()


def week_range(value: date) -> tuple[date, date]:
    """Return the Monday and Sunday covering the given date."""
    monday = value - timedelta(days=value.weekday())
    return monday, monday + timedelta(days=6)


def week_id(value: date) -> str:
    """Return the stable week identifier: the Monday date, which never collides across years."""
    return week_range(value)[0].isoformat()


def date_range(start: date, end: date) -> list[date]:
    """Return every date from start to end inclusive."""
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def weekday_label(value: date) -> str:
    """Return the Chinese weekday label used in previews and exports."""
    return WEEKDAY_NAMES[value.weekday()]


def month_bounds(month: str) -> tuple[date, date, int]:
    """Parse YYYY-MM into its first day, last day and day count."""
    try:
        year_text, month_text = month.split("-")
        year, month_number = int(year_text), int(month_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError("month 参数必须是 YYYY-MM") from exc
    if not 1 <= month_number <= 12:
        raise ValueError("month 参数必须是 YYYY-MM")
    first = date(year, month_number, 1)
    next_month = date(year + 1, 1, 1) if month_number == 12 else date(year, month_number + 1, 1)
    last = next_month - timedelta(days=1)
    return first, last, last.day
