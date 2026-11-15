from __future__ import annotations

from datetime import date, datetime


def buddhist_yymm(when: date | datetime | None = None) -> str:
    when = when or date.today()
    if isinstance(when, datetime):
        when = when.date()
    yy = when.year + 543
    return f"{yy % 100:02d}{when.month:02d}"


def tad_prefix(when: date | datetime | None = None) -> str:
    return f"TAD{buddhist_yymm(when)}-"


def cntad_prefix(when: date | datetime | None = None) -> str:
    return f"CNTAD{buddhist_yymm(when)}-"


def format_tad(seq: int, when: date | datetime | None = None) -> str:
    n = max(1, int(seq))
    return f"{tad_prefix(when)}{n:03d}"


def format_cntad(seq: int, when: date | datetime | None = None) -> str:
    n = max(1, int(seq))
    return f"{cntad_prefix(when)}{n:03d}"
