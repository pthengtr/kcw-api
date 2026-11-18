"""Persist online-sale TAD/CNTAD print HTML for the VAT register."""

from __future__ import annotations

import re
from typing import Any

from src.db.engine import get_engine

_AUTOPRINT_RE = re.compile(
    r"setTimeout\s*\(\s*function\s*\(\s*\)\s*\{\s*window\.print\s*\(\s*\)\s*;\s*\}\s*,\s*200\s*\)\s*;",
    re.I,
)
_PRINT_RE = re.compile(r"window\.print\s*\(\s*\)\s*;", re.I)


def strip_autoprint(html: str) -> str:
    text = _AUTOPRINT_RE.sub("", html or "")
    return _PRINT_RE.sub("", text)


def save_bill_sheet(billno: str, *, kind: str, html: str) -> None:
    exact = (billno or "").strip().upper()
    key = (kind or "").strip().lower()
    body = strip_autoprint(html).strip()
    if not exact or key not in {"tad", "cntad"} or not body:
        return
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            insert into online_sale.bill_sheets (billno, kind, html, updated_at)
            values (%s, %s, %s, now())
            on conflict (billno) do update
              set kind = excluded.kind,
                  html = excluded.html,
                  updated_at = now()
            """,
            (exact, key, body),
        )


def get_bill_sheet(billno: str) -> dict[str, Any] | None:
    exact = (billno or "").strip().upper()
    if not exact:
        return None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                """
                select billno, kind, html, updated_at
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
    }
