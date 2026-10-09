"""Build the to-order list: HQ ICLOW rows plus AI safe-stock lines."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from src.hq_po.group import group_by_vendor, sort_products
from src.hq_po.iclow_read import fetch_to_order_rows, fetch_vendor_names
from src.hq_po.insight import annotate_iclow_items, insight_only_lines, load_insight_policies
from src.hq_po.stock import fetch_dual_stock

logger = logging.getLogger(__name__)

_INSIGHT_TTL_SEC = 120.0
_insight_lock = threading.Lock()
_insight_cache: tuple[float, frozenset[str], list[dict[str, Any]]] | None = None


def _attach_stock(item: dict[str, Any], hq: dict[str, Any] | None, syp: dict[str, Any] | None) -> None:
    if hq is None or syp is None:
        item["hq_qtyoh2"] = None
        item["syp_qtyoh2"] = None
        item["company_qtyoh2"] = None
        return
    hq_qty = float(hq.get("qtyoh2") or 0)
    syp_qty = float(syp.get("qtyoh2") or 0)
    item["hq_qtyoh2"] = hq_qty
    item["syp_qtyoh2"] = syp_qty
    item["company_qtyoh2"] = hq_qty + syp_qty
    item["mtp2"] = float(hq.get("mtp2") or syp.get("mtp2") or 1) or 1.0
    item["hq_blocked"] = bool(hq.get("blocked"))
    if not item.get("descr"):
        item["descr"] = (hq.get("descr") or syp.get("descr") or "").strip()
    if not item.get("mcode"):
        item["mcode"] = (hq.get("mcode") or syp.get("mcode") or "").strip()
    if not item.get("ui"):
        item["ui"] = (hq.get("ui1") or syp.get("ui1") or "").strip()


def _iclow_item(row: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    vendor = row["vendor"]
    return {
        "iclow_id": row["iclow_id"],
        "vendor": vendor,
        "vendor_name": names.get(vendor),
        "bcode": row["bcode"],
        "descr": row["descr"],
        "mcode": row["mcode"],
        "qty": row["qty"],
        "ui": row["ui"],
        "source": "iclow",
        "confirmable": True,
        "hq_qtyoh2": None,
        "syp_qtyoh2": None,
        "company_qtyoh2": None,
        "mtp2": 1.0,
        "hq_blocked": False,
        "propose_meta": None,
    }


def _cached_insight_only(
    policies: dict[str, dict[str, Any]], iclow_bcodes: set[str]
) -> list[dict[str, Any]]:
    global _insight_cache
    key = frozenset(iclow_bcodes)
    now_m = time.monotonic()
    with _insight_lock:
        cached = _insight_cache
        if cached and (now_m - cached[0]) <= _INSIGHT_TTL_SEC and cached[1] == key:
            return list(cached[2])
    codes = [b for b in policies if b not in iclow_bcodes]
    hq, syp, ok = fetch_dual_stock(codes) if codes else ({}, {}, True)
    lines = (
        insight_only_lines(policies, iclow_bcodes=iclow_bcodes, hq_icmas=hq, syp_icmas=syp)
        if ok
        else []
    )
    with _insight_lock:
        _insight_cache = (time.monotonic(), key, lines)
    return lines


def build_suggest() -> dict[str, Any]:
    rows = fetch_to_order_rows()
    try:
        names = fetch_vendor_names([row["vendor"] for row in rows])
    except Exception:
        logger.warning("hq po vendor name lookup failed", exc_info=True)
        names = {}
    items = [_iclow_item(row, names) for row in rows]
    bcodes = [item["bcode"] for item in items if item.get("bcode")]
    hq, syp, stock_ok = fetch_dual_stock(bcodes)
    if stock_ok:
        for item in items:
            bcode = item.get("bcode") or ""
            hq_meta = hq.get(bcode)
            syp_meta = syp.get(bcode)
            if hq_meta is None or syp_meta is None:
                # Missing ICMAS row means that site has no stock record.
                # A failed site read is handled by stock_ok above.
                hq_meta = hq_meta or {"qtyoh2": 0, "mtp2": 1, "blocked": False}
                syp_meta = syp_meta or {"qtyoh2": 0, "mtp2": 1, "blocked": False}
            _attach_stock(item, hq_meta, syp_meta)
    policies = load_insight_policies() if stock_ok else {}
    if policies:
        annotate_iclow_items(items, policies)
        iclow_bcodes = {item["bcode"] for item in items if item.get("bcode")}
        extra = _cached_insight_only(policies, iclow_bcodes)
        try:
            extra_names = fetch_vendor_names([line.get("vendor") or "" for line in extra])
        except Exception:
            logger.warning("hq po insight vendor name lookup failed", exc_info=True)
            extra_names = {}
        for line in extra:
            vendor = line.get("vendor") or ""
            line["vendor_name"] = extra_names.get(vendor)
        items.extend(extra)
    return {
        "items": sort_products(items),
        "vendors": group_by_vendor(items),
        "stock_ok": stock_ok,
    }
