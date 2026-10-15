"""On-demand same-product lookup for the HQ PO line.

Confirmed replacements come from the catalog group. Same เบอร์แท้ and เบอร์โรงงาน
come from the live substitute suggestions. Nothing here runs until the buyer
opens สินค้าแทน on one line.
"""

from __future__ import annotations

import logging
from typing import Any

from src.hq_po.guards import HqPoError
from src.hq_po.iclow_read import (
    fetch_bcode_suppliers,
    fetch_sheet_products,
    supplier_choices,
)
from src.hq_po.stock import fetch_dual_stock
from src.hq_po.suggest import _positive_money

logger = logging.getLogger(__name__)

_PEER_CAP = 24
_SECTION_ORDER = ("catalog", "pcode", "mcode", "other")


def peer_section(sources: list[str] | None, *, in_catalog: bool) -> str:
    """Catalog wins. A genuine-number match wins over a factory-number match."""
    if in_catalog:
        return "catalog"
    found = {str(src or "").strip() for src in (sources or []) if str(src or "").strip()}
    if "pcode" in found:
        return "pcode"
    if "mcode" in found:
        return "mcode"
    return "other"


def section_label(key: str, *, pcode: str = "", mcode: str = "") -> str:
    if key == "catalog":
        return "กลุ่มทดแทน"
    if key == "pcode":
        code = (pcode or "").strip()
        return f"เบอร์แท้เดียวกัน {code}".strip()
    if key == "mcode":
        code = (mcode or "").strip()
        return f"เบอร์โรงงานเดียวกัน {code}".strip()
    return "แนะนำอื่น"


def group_peer_hits(
    *,
    catalog: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    pcode: str = "",
    mcode: str = "",
) -> list[dict[str, Any]]:
    """One row per product code. Confirmed replacements are not repeated below."""
    rows: dict[str, dict[str, Any]] = {}
    catalog_codes: set[str] = set()
    for member in catalog or []:
        code = str(member.get("bcode") or "").strip()
        if not code or code in catalog_codes:
            continue
        catalog_codes.add(code)
        rows[code] = {
            "bcode": code,
            "descr": str(member.get("descr") or "").strip(),
            "sources": ["catalog"],
            "section": "catalog",
        }
    for hit in suggestions or []:
        code = str(hit.get("bcode") or "").strip()
        if not code:
            continue
        sources = [str(src).strip() for src in (hit.get("sources") or []) if str(src or "").strip()]
        primary = str(hit.get("source") or "").strip()
        if primary and primary not in sources:
            sources.insert(0, primary)
        if code in rows:
            if hit.get("descr") and not rows[code].get("descr"):
                rows[code]["descr"] = str(hit.get("descr") or "").strip()
            continue
        rows[code] = {
            "bcode": code,
            "descr": str(hit.get("descr") or "").strip(),
            "sources": sources,
            "section": peer_section(sources, in_catalog=False),
        }
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in _SECTION_ORDER}
    for row in rows.values():
        grouped.setdefault(str(row["section"]), []).append(row)
    out: list[dict[str, Any]] = []
    for key in _SECTION_ORDER:
        lines = grouped.get(key) or []
        if not lines:
            continue
        lines.sort(key=lambda row: str(row.get("bcode") or ""))
        out.append(
            {
                "key": key,
                "label": section_label(key, pcode=pcode, mcode=mcode),
                "lines": lines,
            }
        )
    return out


def _catalog_peers(bcode: str) -> list[dict[str, Any]]:
    try:
        from src.substitutes.db import get_substitutes_supabase_client, list_peers
    except Exception:
        logger.warning("hq po substitute catalog import failed", exc_info=True)
        return []
    try:
        return list(list_peers(get_substitutes_supabase_client(), bcode) or [])
    except Exception:
        logger.warning("hq po substitute catalog lookup failed", exc_info=True)
        return []


def _live_peers(bcode: str) -> list[dict[str, Any]]:
    try:
        from src.substitutes.suggest import suggest_for_bcode
    except Exception:
        logger.warning("hq po live peer import failed", exc_info=True)
        return []
    try:
        return list(suggest_for_bcode(bcode, ship_branch="HQ", cap=_PEER_CAP) or [])
    except Exception:
        logger.warning("hq po live peer lookup failed", exc_info=True)
        return []


def _money(value: Any) -> float | None:
    return _positive_money(value)


def _decorate(
    row: dict[str, Any],
    *,
    product: dict[str, Any],
    hq: dict[str, Any] | None,
    syp: dict[str, Any] | None,
    suppliers: list[dict[str, Any]],
) -> dict[str, Any]:
    ui1 = str(product.get("ui") or (hq or {}).get("ui1") or "").strip()
    ui2 = str(product.get("ui2") or (hq or {}).get("ui2") or "").strip()
    try:
        mtp2 = float(product.get("mtp2") or (hq or {}).get("mtp2") or 0)
    except (TypeError, ValueError):
        mtp2 = 0.0
    if mtp2 <= 0:
        mtp2 = 1.0
    hq_qty = None if hq is None else float(hq.get("qtyoh2") or 0)
    syp_qty = None if syp is None else float(syp.get("qtyoh2") or 0)
    company = None if hq_qty is None or syp_qty is None else hq_qty + syp_qty
    vendor = ""
    vendor_name = ""
    if suppliers:
        vendor = str(suppliers[0].get("acctno") or "").strip()
        vendor_name = str(suppliers[0].get("name") or "").strip()
    return {
        "bcode": row["bcode"],
        "descr": str(product.get("descr") or row.get("descr") or "").strip(),
        "model": str(product.get("model") or "").strip(),
        "brand": str(product.get("brand") or "").strip(),
        "pcode": str(product.get("pcode") or "").strip(),
        "mcode": str(product.get("mcode") or "").strip(),
        "ui": ui1,
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
        "price": _money(product.get("price1")),
        "cost": _money(product.get("costlast")) or _money(product.get("costnet")),
        "hq_qtyoh2": hq_qty,
        "syp_qtyoh2": syp_qty,
        "company_qtyoh2": company,
        "vendor": vendor,
        "vendor_name": vendor_name,
        "suppliers": suppliers,
        "sources": list(row.get("sources") or []),
    }


def load_peers(bcode: str) -> dict[str, Any]:
    """Confirmed replacements plus same เบอร์แท้ / เบอร์โรงงาน for one product."""
    code = str(bcode or "").strip()
    if not code:
        raise HqPoError("missing", "ไม่มีรหัสสินค้า")
    source = fetch_sheet_products([code]).get(code) or {}
    groups = group_peer_hits(
        catalog=_catalog_peers(code),
        suggestions=_live_peers(code),
        pcode=str(source.get("pcode") or "").strip(),
        mcode=str(source.get("mcode") or "").strip(),
    )
    codes = [line["bcode"] for group in groups for line in group["lines"]]
    products = fetch_sheet_products(codes) if codes else {}
    hq: dict[str, dict[str, Any]] = {}
    syp: dict[str, dict[str, Any]] = {}
    stock_ok = False
    if codes:
        hq, syp, stock_ok = fetch_dual_stock(codes, refresh=True)
    history: dict[str, list[dict[str, Any]]] = {}
    catalog: dict[str, dict[str, str]] = {}
    if codes:
        try:
            history, catalog = fetch_bcode_suppliers(codes)
        except Exception:
            logger.warning("hq po peer supplier lookup failed", exc_info=True)
    for group in groups:
        decorated = []
        for line in group["lines"]:
            peer = str(line.get("bcode") or "").strip()
            card = catalog.get(peer) or {}
            choices = supplier_choices(
                history.get(peer) or [],
                catalog=str(card.get("acctno") or ""),
                catalog_name=str(card.get("name") or ""),
            )
            hq_meta = hq.get(peer) if stock_ok else None
            syp_meta = syp.get(peer) if stock_ok else None
            if stock_ok:
                hq_meta = hq_meta or {"qtyoh2": 0, "mtp2": 1}
                syp_meta = syp_meta or {"qtyoh2": 0, "mtp2": 1}
            decorated.append(
                _decorate(
                    line,
                    product=products.get(peer) or {},
                    hq=hq_meta,
                    syp=syp_meta,
                    suppliers=choices,
                )
            )
        group["lines"] = decorated
    return {
        "bcode": code,
        "pcode": str(source.get("pcode") or "").strip(),
        "mcode": str(source.get("mcode") or "").strip(),
        "groups": groups,
    }
