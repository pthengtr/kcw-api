"""Live PARTS9 sales-revenue rules — same as fn_bi_sales_bill_excluded_from_revenue.

Billno prefixes, JOURMODE=0, CANCELED, SA/3SA, TF/TFV/TAR, CNTF/3CNTF.
TAD / CNTAD report as ONLINE, not HQ store.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

BKK = ZoneInfo("Asia/Bangkok")
MAX_LIVE_DAYS = 92

_EXCL = re.compile(r"^(3)?(CNTF|SA|TF|TAR)", re.I)
_STD_PREFIXES = (
    ("TFV", "TFV"),
    ("TAR", "TAR"),
    ("TAD", "TAD"),
    ("TF", "TF"),
    ("TD", "TD"),
    ("TR", "TR"),
    ("DN", "DN"),
    ("CN", "CN"),
)


def today_bkk() -> date:
    return datetime.now(BKK).date()


def parse_iso_date(value: str | None) -> date | None:
    raw = (value or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def resolve_range(dfrom: str | None, dto: str | None) -> tuple[date, date]:
    today = today_bkk()
    start = parse_iso_date(dfrom) or today.replace(day=1)
    end = parse_iso_date(dto) or today
    if start > end:
        start, end = end, start
    span = (end - start).days + 1
    if span > MAX_LIVE_DAYS:
        raise ValueError(f"live range max {MAX_LIVE_DAYS} days (asked {span})")
    return start, end


def previous_range(start: date, end: date) -> tuple[date, date]:
    span = (end - start).days
    prev_to = start - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span)
    return prev_from, prev_to


def billno_core(billno: str) -> str:
    b = (billno or "").strip().upper()
    if b.startswith("3") and len(b) > 1:
        return b[1:]
    return b


def billtype_std(billno: str) -> str:
    core = billno_core(billno)
    for prefix, std in _STD_PREFIXES:
        if core.startswith(prefix):
            return std
    return "UNKNOWN"


def excluded_from_revenue(billno: str) -> bool:
    b = (billno or "").strip().upper()
    return bool(_EXCL.match(b))


def reporting_branch(*, site: str, billno: str, std: str | None = None) -> str:
    std = std or billtype_std(billno)
    core = billno_core(billno)
    if std == "TAD" or core.startswith("CNTAD"):
        return "ONLINE"
    return "SYP" if (site or "").lower() == "syp" else "HQ"


def channel(std: str, billno: str) -> str:
    if std == "TAD" or billno_core(billno).startswith("CNTAD"):
        return "ONLINE"
    return "COUNTER"


def sales_type(std: str, billno: str, tax: float) -> str:
    if std in ("TAD", "TD", "TR"):
        return "VAT"
    if std in ("CN", "DN") and tax != 0:
        return "VAT"
    core = billno_core(billno)
    if std == "UNKNOWN" and (core.startswith("IV") or core.startswith("TA")):
        return "VAT"
    return "NON_VAT"


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0
