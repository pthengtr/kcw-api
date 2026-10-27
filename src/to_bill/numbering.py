from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")


def buddhist_yymm(on: date | datetime | None = None) -> str:
    if isinstance(on, datetime):
        day = on.astimezone(BKK).date()
    elif isinstance(on, date):
        day = on
    else:
        day = datetime.now(BKK).date()
    return f"{(day.year + 543) % 100:02d}{day.month:02d}"


def format_docno(yymm: str, seq: int) -> str:
    """TO6910-001. Past 999 the sequence is not truncated."""
    token = (yymm or "").strip()
    if len(token) != 4 or not token.isdigit():
        raise ValueError("yymm")
    number = int(seq)
    if number < 1:
        raise ValueError("seq")
    if number < 1000:
        return f"TO{token}-{number:03d}"
    return f"TO{token}-{number}"


def month_bounds(yymm: str) -> tuple[datetime, datetime]:
    """Bangkok month window for a Buddhist YYMM such as 6910."""
    token = (yymm or "").strip()
    if len(token) != 4 or not token.isdigit():
        raise ValueError("yymm")
    year = int(token[:2]) + 1957
    month = int(token[2:])
    if month < 1 or month > 12:
        raise ValueError("yymm")
    start = datetime(year, month, 1, tzinfo=BKK)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=BKK)
    else:
        end = datetime(year, month + 1, 1, tzinfo=BKK)
    return start, end
