from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

_REMARK_PATTERN = re.compile(
    r"^(.+?)-บิลเดือน\s+(\d{1,2})/(\d{4})(?:\s*/\s*(.+))?$"
)
_REMARK_EXTRA_MAX = 200
_REMARK_MAX = 500


def parse_bill_month(raw: str | None) -> date | None:
    """Parse YYYY-MM or YYYY-MM-DD to first day of month."""
    text = (raw or "").strip()
    if not text:
        return None
    if len(text) >= 7 and text[4] == "-":
        ym = text[:7]
        try:
            dt = datetime.strptime(f"{ym}-01", "%Y-%m-%d").date()
            return dt
        except ValueError:
            return None
    return None


def bill_month_to_ym(d: date | str | None) -> str:
    """Return YYYY-MM for month input value."""
    if not d:
        return ""
    if isinstance(d, str):
        return d[:7] if len(d) >= 7 else ""
    return d.strftime("%Y-%m")


def format_bill_month_display(d: date | str | None) -> str:
    """Return m/yyyy for display."""
    if not d:
        return ""
    if isinstance(d, str):
        if len(d) >= 7 and d[4] == "-":
            y, m = d[:4], int(d[5:7])
            return f"{m}/{y}"
        return ""
    return f"{d.month}/{d.year}"


def compose_remark(acctno: str, bill_month: date | None, remark_extra: str = "") -> str:
    """Build canonical remark string from structured fields."""
    acct = (acctno or "").strip()
    extra = (remark_extra or "").strip()[:_REMARK_EXTRA_MAX]
    if bill_month:
        label = f"{acct}-บิลเดือน {bill_month.month}/{bill_month.year}"
        if extra:
            return f"{label} / {extra}"[:_REMARK_MAX]
        return label[:_REMARK_MAX]
    if extra:
        return extra[:_REMARK_MAX]
    return ""


def parse_legacy_remark(remark: str) -> dict[str, Any]:
    """Parse composed remark into structured parts."""
    text = (remark or "").strip()
    if not text:
        return {"bill_month": None, "remark_extra": ""}
    m = _REMARK_PATTERN.match(text)
    if not m:
        return {"bill_month": None, "remark_extra": text[:_REMARK_EXTRA_MAX]}
    month = int(m.group(2))
    year = int(m.group(3))
    try:
        bm = date(year, month, 1)
    except ValueError:
        return {"bill_month": None, "remark_extra": text[:_REMARK_EXTRA_MAX]}
    extra = (m.group(4) or "").strip()[:_REMARK_EXTRA_MAX]
    return {"bill_month": bm, "remark_extra": extra}


def resolve_remark_fields(
    acctno: str,
    *,
    bill_month: str | None = None,
    remark_extra: str | None = None,
    remark: str | None = None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve structured remark fields for create/update.

    When bill_month or remark_extra is provided (including explicit empty string
    via remark_extra), structured mode is used. Otherwise falls back to raw remark.
    """
    existing = existing or {}
    structured_sent = bill_month is not None or remark_extra is not None

    if structured_sent:
        bm = parse_bill_month(bill_month) if bill_month else None
        extra = (remark_extra or "").strip()[:_REMARK_EXTRA_MAX]
        composed = compose_remark(acctno, bm, extra)
        return {
            "bill_month": bm.isoformat() if bm else None,
            "remark_extra": extra,
            "remark": composed,
        }

    if remark is not None:
        text = (remark or "").strip()[:_REMARK_MAX]
        parsed = parse_legacy_remark(text)
        bm = parsed.get("bill_month")
        extra = parsed.get("remark_extra") or ""
        return {
            "bill_month": bm.isoformat() if bm else None,
            "remark_extra": extra,
            "remark": text,
        }

    # No change requested
    bm_existing = existing.get("bill_month")
    if isinstance(bm_existing, str) and bm_existing:
        bm_existing = bm_existing[:10]
    extra_existing = (existing.get("remark_extra") or "").strip()
    composed_existing = (existing.get("remark") or "").strip()
    return {
        "bill_month": bm_existing if bm_existing else None,
        "remark_extra": extra_existing,
        "remark": composed_existing,
    }
