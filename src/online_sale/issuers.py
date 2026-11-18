"""Snapshot printable issuer names for TAD/CNTAD at issue time."""

from __future__ import annotations

from typing import Any

from src.db.engine import get_engine
from src.staff.profiles import issuer_label_for_actor


def save_doc_issuer(
    billno: str,
    *,
    line_user_id: str = "",
    display_name: str = "",
    issuer_label: str = "",
) -> dict[str, Any]:
    """Write-once snapshot. Reprints and edits must not change the label."""
    exact = (billno or "").strip().upper()
    if not exact:
        return {}
    label = (issuer_label or "").strip() or issuer_label_for_actor(
        line_user_id=line_user_id,
        display_name=display_name,
    )
    if not label:
        label = (display_name or line_user_id or "unknown").strip()
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            insert into online_sale.doc_issuers (
              billno, line_user_id, line_display_name, issuer_label
            )
            values (%s, %s, %s, %s)
            on conflict (billno) do nothing
            """,
            (
                exact,
                (line_user_id or "").strip() or None,
                (display_name or "").strip() or None,
                label,
            ),
        )
    return {
        "billno": exact,
        "line_user_id": (line_user_id or "").strip(),
        "line_display_name": (display_name or "").strip(),
        "issuer_label": label,
    }


def get_doc_issuer(billno: str) -> dict[str, Any] | None:
    exact = (billno or "").strip().upper()
    if not exact:
        return None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                """
                select billno, line_user_id, line_display_name, issuer_label
                from online_sale.doc_issuers
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
        "line_user_id": row[1] or "",
        "line_display_name": row[2] or "",
        "issuer_label": row[3] or "",
    }


def resolve_print_issuer(bill: dict[str, Any]) -> str:
    """Prefer snapshot; fall back to remapping SIMAS.SALE for older bills."""
    if str(bill.get("issuer_label") or "").strip():
        label = str(bill["issuer_label"]).strip()
        # Stale callers may put the raw LINE/POS stamp in issuer_label — remap.
        remapped = issuer_label_for_actor(display_name=label)
        return remapped or label
    billno = str(bill.get("billno") or "")
    snap = get_doc_issuer(billno)
    if snap and snap.get("issuer_label"):
        label = str(snap["issuer_label"]).strip()
        remapped = issuer_label_for_actor(display_name=label)
        return remapped or label
    sale = str(bill.get("sale") or "").strip()
    return issuer_label_for_actor(display_name=sale) or sale
