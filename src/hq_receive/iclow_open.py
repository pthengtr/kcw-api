"""Read HQ ค้างรับ from ICLOW. Never writes RECEIVED here."""

from __future__ import annotations

from typing import Any

from src.hq_po.iclow_read import (
    fetch_incoming_lines,
    fetch_sheet_products,
    fetch_vendor_cards,
    search_vendors as search_apmas_vendors,
    thumb_url,
)


def _po_key(row: dict[str, Any]) -> str:
    return str(row.get("hq_po_docno") or row.get("docno") or "").strip()


def _line_preview(row: dict[str, Any]) -> dict[str, Any]:
    """Compact product row shown under an open PO checkbox."""
    return {
        "bcode": str(row.get("bcode") or "").strip(),
        "descr": str(row.get("descr") or "").strip(),
        "model": str(row.get("model") or "").strip(),
        "brand": str(row.get("brand") or "").strip(),
        "pcode": str(row.get("pcode") or "").strip(),
        "mcode": str(row.get("mcode") or "").strip(),
        "photo": str(row.get("photo") or "").strip(),
        "qty": float(row.get("qty") or 0),
        "ui": str(row.get("ui") or "").strip(),
    }


def _enrich_costs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach ICMAS cost + identity fields and a product photo URL."""
    bcodes = [str(r.get("bcode") or "").strip() for r in rows if r.get("bcode")]
    products = fetch_sheet_products(bcodes) if bcodes else {}
    photo_cache: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    for row in rows:
        bcode = str(row.get("bcode") or "").strip()
        product = products.get(bcode) or {}
        costlast = float(product.get("costlast") or 0) or 0.0
        costnet = float(product.get("costnet") or 0) or 0.0
        cost = costlast if costlast > 0 else costnet
        if bcode and bcode not in photo_cache:
            photo_cache[bcode] = thumb_url(bcode)
        out.append(
            {
                **row,
                "descr": str(product.get("descr") or row.get("descr") or "").strip(),
                "model": str(product.get("model") or row.get("model") or "").strip(),
                "brand": str(product.get("brand") or row.get("brand") or "").strip(),
                "pcode": str(product.get("pcode") or row.get("pcode") or "").strip(),
                "mcode": str(product.get("mcode") or row.get("mcode") or "").strip(),
                "location1": str(product.get("location1") or row.get("location1") or "").strip(),
                "code1": str(product.get("code1") or row.get("code1") or "").strip(),
                "ui": str(product.get("ui") or row.get("ui") or "").strip(),
                "photo": photo_cache.get(bcode) or "",
                "costlast": costlast if costlast > 0 else None,
                "costnet": costnet if costnet > 0 else None,
                "cost": cost,
                "price1": product.get("price1"),
            }
        )
    return out


def list_open_lines(
    *,
    acctno: str = "",
    q: str = "",
    po_docnos: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Ordered-not-received HQ ICLOW lines, optionally filtered by vendor / PO / search."""
    acct = (acctno or "").strip().upper()
    needle = (q or "").strip().lower()
    wanted_pos = {
        str(p or "").strip().upper()
        for p in (po_docnos or [])
        if str(p or "").strip()
    }
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
        enriched = {
            **row,
            "vendor_name": card.get("name") or "",
            "vendor_term": card.get("term") or "",
            "hq_po_docno": (po.get("docno") or row.get("docno") or "").strip(),
            "hq_po_line_id": po.get("line_id"),
            "hq_po_order_id": po.get("order_id"),
        }
        if wanted_pos:
            key = _po_key(enriched).upper()
            if key not in wanted_pos:
                continue
        out.append(enriched)
    return _enrich_costs(out)


def list_open_pos(*, acctno: str = "") -> list[dict[str, Any]]:
    """Open POs for a vendor (or all), rolled up from ค้างรับ lines.

    Each PO includes a ``lines`` preview so the operator can verify the bill
    without opening it first.
    """
    lines = list_open_lines(acctno=acctno)
    by: dict[str, dict[str, Any]] = {}
    for line in lines:
        po = _po_key(line) or "(ไม่มีเลข PO)"
        bucket = by.setdefault(
            po,
            {
                "po_docno": po,
                "vendor": (line.get("vendor") or "").strip(),
                "vendor_name": line.get("vendor_name") or "",
                "line_count": 0,
                "qty_total": 0.0,
                "docdate": line.get("docdate"),
                "lines": [],
            },
        )
        bucket["line_count"] += 1
        bucket["qty_total"] += float(line.get("qty") or 0)
        bucket["lines"].append(_line_preview(line))
        if line.get("vendor_name"):
            bucket["vendor_name"] = line["vendor_name"]
        if line.get("docdate") and (
            not bucket.get("docdate") or str(line["docdate"]) < str(bucket["docdate"])
        ):
            bucket["docdate"] = line["docdate"]
    rows = list(by.values())
    rows.sort(key=lambda r: (str(r.get("docdate") or ""), r.get("po_docno") or ""), reverse=True)
    return rows


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
