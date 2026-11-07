"""Read HQ ค้างรับ from ICLOW. Never writes RECEIVED here."""

from __future__ import annotations

from typing import Any

from src.hq_po.iclow_read import (
    fetch_incoming_lines,
    fetch_vendor_cards,
    search_vendors as search_apmas_vendors,
)


def list_open_lines(*, acctno: str = "", q: str = "") -> list[dict[str, Any]]:
    """Ordered-not-received HQ ICLOW lines, optionally filtered by vendor / search."""
    acct = (acctno or "").strip().upper()
    needle = (q or "").strip().lower()
    rows = fetch_incoming_lines()
    if acct:
        rows = [r for r in rows if (r.get("vendor") or "").strip().upper() == acct]
    if needle:
        rows = [
            r
            for r in rows
            if needle in (r.get("bcode") or "").lower()
            or needle in (r.get("descr") or "").lower()
            or needle in (r.get("docno") or "").lower()
            or needle in (r.get("vendor") or "").lower()
            or needle in (r.get("mcode") or "").lower()
        ]

    iclow_ids = [int(r["iclow_id"]) for r in rows if r.get("iclow_id")]
    po_by_iclow: dict[int, dict[str, Any]] = {}
    try:
        from src.hq_po.db import get_hq_po_supabase_client, open_lines_for_iclow

        client = get_hq_po_supabase_client()
        po_by_iclow = open_lines_for_iclow(client, iclow_ids)
    except Exception:
        po_by_iclow = {}

    vendors = fetch_vendor_cards([r.get("vendor") or "" for r in rows])
    out: list[dict[str, Any]] = []
    for row in rows:
        vendor = (row.get("vendor") or "").strip()
        card = vendors.get(vendor) or {}
        po = po_by_iclow.get(int(row["iclow_id"])) or {}
        out.append(
            {
                **row,
                "vendor_name": card.get("name") or "",
                "vendor_term": card.get("term") or "",
                "hq_po_docno": (po.get("docno") or row.get("docno") or "").strip(),
                "hq_po_line_id": po.get("line_id"),
                "hq_po_order_id": po.get("order_id"),
            }
        )
    return out


def list_open_vendors(*, q: str = "") -> list[dict[str, Any]]:
    """Vendors that still have ค้างรับ lines, with counts."""
    lines = list_open_lines()
    by: dict[str, dict[str, Any]] = {}
    for line in lines:
        acct = (line.get("vendor") or "").strip()
        if not acct:
            continue
        bucket = by.setdefault(
            acct,
            {
                "acctno": acct,
                "name": line.get("vendor_name") or acct,
                "line_count": 0,
                "qty_total": 0.0,
            },
        )
        bucket["line_count"] += 1
        bucket["qty_total"] += float(line.get("qty") or 0)
        if line.get("vendor_name"):
            bucket["name"] = line["vendor_name"]

    needle = (q or "").strip().lower()
    rows = list(by.values())
    if needle:
        rows = [
            r
            for r in rows
            if needle in (r.get("acctno") or "").lower()
            or needle in (r.get("name") or "").lower()
        ]
    rows.sort(key=lambda r: ((r.get("name") or "").lower(), r.get("acctno") or ""))
    return rows


def search_vendors(q: str, *, limit: int = 30) -> list[dict[str, Any]]:
    """Open-vendor list when q is empty; otherwise APMAS search + open counts."""
    open_map = {r["acctno"]: r for r in list_open_vendors()}
    if not (q or "").strip():
        return list(open_map.values())[:limit]

    hits = search_apmas_vendors(q, limit=limit)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        acct = str(hit.get("acctno") or hit.get("ACCTNO") or "").strip()
        name = str(hit.get("name") or hit.get("ACCTNAME") or "").strip()
        if not acct or acct in seen:
            continue
        seen.add(acct)
        open_row = open_map.get(acct) or {}
        out.append(
            {
                "acctno": acct,
                "name": name or open_row.get("name") or acct,
                "line_count": int(open_row.get("line_count") or 0),
                "qty_total": float(open_row.get("qty_total") or 0),
                "has_open": bool(open_row),
            }
        )
        if len(out) >= limit:
            break
    return out
