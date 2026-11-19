"""Persist online-sale TAD/CNTAD print HTML for the VAT register."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

from src.db.engine import get_engine

_AUTOPRINT_RE = re.compile(
    r"setTimeout\s*\(\s*function\s*\(\s*\)\s*\{\s*window\.print\s*\(\s*\)\s*;\s*\}\s*,\s*200\s*\)\s*;",
    re.I,
)
_PRINT_RE = re.compile(r"window\.print\s*\(\s*\)\s*;", re.I)
# CNTAD reason lives in `.cn-box .reason .v` — recover when reprint omits ?reason=.
_REASON_RE = re.compile(
    r"เหตุผลที่ออกใบลดหนี้</span>\s*<span class=['\"]v['\"]>(.*?)</span>",
    re.I | re.S,
)


def strip_autoprint(html: str) -> str:
    text = _AUTOPRINT_RE.sub("", html or "")
    return _PRINT_RE.sub("", text)


def reason_from_sheet_html(html: str | None) -> str:
    """Pull a non-empty CNTAD reason out of previously snapshotted HTML."""
    match = _REASON_RE.search(html or "")
    if not match:
        return ""
    raw = html_lib.unescape(match.group(1) or "").strip()
    if not raw or raw in {"—", "-", "–"}:
        return ""
    return raw


def save_bill_sheet(
    billno: str, *, kind: str, html: str, reason: str | None = None
) -> None:
    exact = (billno or "").strip().upper()
    key = (kind or "").strip().lower()
    body = strip_autoprint(html).strip()
    if not exact or key not in {"tad", "cntad"} or not body:
        return
    reason_text = (reason if reason is not None else "").strip() or None
    if key == "cntad" and reason_text is None:
        # Keep a previously stored reason when reprint regenerates without one.
        reason_text = get_bill_sheet_reason(exact) or reason_from_sheet_html(body) or None
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            insert into online_sale.bill_sheets (billno, kind, html, reason, updated_at)
            values (%s, %s, %s, %s, now())
            on conflict (billno) do update
              set kind = excluded.kind,
                  html = excluded.html,
                  reason = coalesce(excluded.reason, online_sale.bill_sheets.reason),
                  updated_at = now()
            """,
            (exact, key, body, reason_text),
        )


def get_bill_sheet_reason(billno: str) -> str:
    exact = (billno or "").strip().upper()
    if not exact:
        return ""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                """
                select reason, html
                from online_sale.bill_sheets
                where billno = %s
                """,
                (exact,),
            ).fetchone()
    except Exception:
        return ""
    if not row:
        return ""
    stored = str(row[0] or "").strip()
    if stored:
        return stored
    return reason_from_sheet_html(str(row[1] or ""))


def get_bill_sheet(billno: str) -> dict[str, Any] | None:
    exact = (billno or "").strip().upper()
    if not exact:
        return None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                """
                select billno, kind, html, updated_at, reason
                from online_sale.bill_sheets
                where billno = %s
                """,
                (exact,),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "billno": row[0],
        "kind": row[1],
        "html": row[2],
        "updated_at": row[3],
        "reason": row[4] or "",
    }
