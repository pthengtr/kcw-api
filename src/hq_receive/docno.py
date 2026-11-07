from __future__ import annotations

from datetime import date, datetime


def buddhist_yymm(when: date | datetime | None = None) -> str:
    when = when or date.today()
    if isinstance(when, datetime):
        when = when.date()
    yy = when.year + 543
    return f"{yy % 100:02d}{when.month:02d}"


def bn_prefix(when: date | datetime | None = None) -> str:
    """KCW purchase bill prefix used on HQ PARTS9 (BN + Buddhist YYMM)."""
    return f"BN{buddhist_yymm(when)}"


def format_bn(seq: int, when: date | datetime | None = None) -> str:
    """BN691100001 style — 5-digit sequence, max 15 chars for PIMAS.BILLNO."""
    n = max(1, int(seq))
    return f"{bn_prefix(when)}{n:05d}"
