"""Build the to-order list: HQ ICLOW rows plus AI safe-stock lines."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from src.hq_po.group import sort_products
from src.hq_po.iclow_read import (
    fetch_bcode_suppliers,
    fetch_incoming_qty,
    fetch_sheet_products,
    fetch_to_order_rows,
    fetch_vendor_names,
    supplier_choices,
)
from src.hq_po.insight import (
    annotate_iclow_items,
    insight_only_lines,
    load_insight_policies,
    load_insight_policies_for,
)
from src.hq_po.stock import fetch_dual_stock, fetch_parts9_qty

logger = logging.getLogger(__name__)

_INSIGHT_TTL_SEC = 300.0
_insight_lock = threading.Lock()
_insight_cache: tuple[float, tuple[Any, ...], list[dict[str, Any]]] | None = None
_insight_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hq-po-insight")
_insight_future: Future | None = None
_insight_future_key: tuple[Any, ...] | None = None


def insight_cache_key(iclow_bcodes: set[str], incoming: dict[str, float]) -> tuple[Any, ...]:
    held = frozenset(
        (str(bcode), round(float(qty), 4))
        for bcode, qty in (incoming or {}).items()
        if str(bcode or "").strip() and float(qty or 0) > 0
    )
    return (frozenset(iclow_bcodes), held)


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
    if not item.get("ui1"):
        item["ui1"] = (hq.get("ui1") or syp.get("ui1") or "").strip()
    if not item.get("ui2"):
        item["ui2"] = (hq.get("ui2") or syp.get("ui2") or "").strip()
    if not item.get("ui"):
        item["ui"] = item.get("ui1") or ""
    if not item.get("model"):
        item["model"] = (hq.get("model") or syp.get("model") or "").strip()
    if not item.get("brand"):
        item["brand"] = (hq.get("brand") or syp.get("brand") or "").strip()
    if not item.get("pcode"):
        item["pcode"] = (hq.get("pcode") or syp.get("pcode") or "").strip()


def _positive_money(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:
        return None
    return round(number, 2)


def attach_catalog(
    items: list[dict[str, Any]],
    products: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Fill ชื่อรุ่น, เบอร์แท้, เบอร์โรงงาน, ยี่ห้อ, ราคา, and ค่า from HQ ICMAS."""
    codes = [str(item.get("bcode") or "").strip() for item in items if item.get("bcode")]
    if not codes:
        return
    if products is None:
        try:
            products = fetch_sheet_products(codes)
        except Exception:
            logger.warning("hq po catalog lookup failed", exc_info=True)
            return
    for item in items:
        product = products.get(str(item.get("bcode") or "").strip()) or {}
        for key in ("model", "brand", "pcode", "mcode"):
            value = str(product.get(key) or "").strip()
            if value:
                item[key] = value
        ui1 = str(product.get("ui") or "").strip()
        if ui1:
            item["ui1"] = ui1
        ui2 = str(product.get("ui2") or "").strip()
        if ui2:
            item["ui2"] = ui2
        try:
            mtp2 = float(product.get("mtp2") or 0)
        except (TypeError, ValueError):
            mtp2 = 0.0
        if mtp2 > 0:
            item["mtp2"] = mtp2
        price = _positive_money(product.get("price1"))
        if price is not None:
            item["price"] = price
        cost = _positive_money(product.get("costlast"))
        if cost is None:
            cost = _positive_money(product.get("costnet"))
        if cost is not None:
            item["cost"] = cost


def suppliers_for_bcode(
    bcode: str,
    *,
    current: str = "",
    current_name: str = "",
) -> list[dict[str, Any]]:
    """Purchase-history suppliers for one product. The waiting list does not call this."""
    code = str(bcode or "").strip()
    if not code:
        return []
    history, catalog = fetch_bcode_suppliers([code])
    card = catalog.get(code) or {}
    return supplier_choices(
        history.get(code) or [],
        current=current,
        current_name=current_name,
        catalog=str(card.get("acctno") or ""),
        catalog_name=str(card.get("name") or ""),
    )


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


def _peek_insight_cache(key: frozenset[str]) -> list[dict[str, Any]] | None:
    now_m = time.monotonic()
    with _insight_lock:
        cached = _insight_cache
        if cached and (now_m - cached[0]) <= _INSIGHT_TTL_SEC and cached[1] == key:
            return list(cached[2])
    return None


def _compute_insight_only(
    policies: dict[str, dict[str, Any]],
    iclow_bcodes: frozenset[str],
    incoming: dict[str, float],
) -> list[dict[str, Any]]:
    """Live gap for products that are not already on the ICLOW list.

    This scans every insight SKU, so it must not block the ICLOW response.
    """
    codes = [b for b in policies if b not in iclow_bcodes]
    hq, syp, ok = fetch_dual_stock(codes) if codes else ({}, {}, True)
    lines = (
        insight_only_lines(
            policies,
            iclow_bcodes=set(iclow_bcodes),
            hq_icmas=hq,
            syp_icmas=syp,
            incoming=incoming,
        )
        if ok
        else []
    )
    if ok and lines:
        shown = [str(line.get("bcode") or "").strip() for line in lines if line.get("bcode")]
        hq2, syp2, ok2 = fetch_dual_stock(shown, refresh=True)
        if ok2:
            subset = {bcode: policies[bcode] for bcode in shown if bcode in policies}
            lines = insight_only_lines(
                subset,
                iclow_bcodes=set(iclow_bcodes),
                hq_icmas=hq2,
                syp_icmas=syp2,
                incoming=incoming,
            )
    global _insight_cache
    try:
        extra_names = fetch_vendor_names([line.get("vendor") or "" for line in lines])
    except Exception:
        logger.warning("hq po insight vendor name lookup failed", exc_info=True)
        extra_names = {}
    for line in lines:
        vendor = line.get("vendor") or ""
        line["vendor_name"] = extra_names.get(vendor)
    with _insight_lock:
        _insight_cache = (time.monotonic(), insight_cache_key(set(iclow_bcodes), incoming), lines)
    return lines


def _ensure_insight_future(
    policies: dict[str, dict[str, Any]],
    iclow_bcodes: set[str],
    incoming: dict[str, float] | None = None,
) -> Future:
    """One scan at a time. A warm cache or an in-flight scan is reused."""
    global _insight_future, _insight_future_key
    held = dict(incoming or {})
    key = insight_cache_key(set(iclow_bcodes), held)
    with _insight_lock:
        cached = _insight_cache
        now_m = time.monotonic()
        if cached and (now_m - cached[0]) <= _INSIGHT_TTL_SEC and cached[1] == key:
            done: Future = Future()
            done.set_result(list(cached[2]))
            return done
        if (
            _insight_future is not None
            and not _insight_future.done()
            and _insight_future_key == key
        ):
            return _insight_future
        _insight_future_key = key
        _insight_future = _insight_executor.submit(
            _compute_insight_only, policies, frozenset(iclow_bcodes), held
        )
        return _insight_future


def _attach_parts9(
    items: list[dict[str, Any]],
    found: dict[str, float] | None = None,
) -> None:
    if found is None:
        codes = [str(item.get("bcode") or "").strip() for item in items]
        try:
            found = fetch_parts9_qty(codes)
        except Exception:
            logger.warning("hq po parts9 qty read failed", exc_info=True)
            return
    for item in items:
        qty = found.get(str(item.get("bcode") or "").strip())
        if qty:
            item["parts9_qty"] = qty


def _catalog_for(bcodes: list[str]) -> dict[str, dict[str, Any]]:
    try:
        return fetch_sheet_products(bcodes)
    except Exception:
        logger.warning("hq po catalog lookup failed", exc_info=True)
        return {}


def build_suggest() -> dict[str, Any]:
    """Waiting lines only. The full AI scan stays on the AI tab."""
    rows = fetch_to_order_rows()
    bcodes = [str(row.get("bcode") or "").strip() for row in rows if str(row.get("bcode") or "").strip()]
    with ThreadPoolExecutor(max_workers=1) as pool:
        catalog_fut = pool.submit(_catalog_for, bcodes)
        try:
            names = fetch_vendor_names([row["vendor"] for row in rows])
        except Exception:
            logger.warning("hq po vendor name lookup failed", exc_info=True)
            names = {}
        hq, syp, stock_ok = fetch_dual_stock(bcodes)
        incoming: dict[str, float] = {}
        try:
            incoming = fetch_incoming_qty()
        except Exception:
            logger.warning("hq po incoming qty read failed", exc_info=True)
        try:
            parts9 = fetch_parts9_qty(bcodes)
        except Exception:
            logger.warning("hq po parts9 qty read failed", exc_info=True)
            parts9 = {}
        try:
            policies = load_insight_policies_for(bcodes) if stock_ok else {}
        except Exception:
            logger.warning("hq po insight policy read failed", exc_info=True)
            policies = {}
        products = catalog_fut.result()
    items = [_iclow_item(row, names) for row in rows]
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
        if policies:
            annotate_iclow_items(items, policies, incoming=incoming)
    _attach_parts9(items, parts9)
    attach_catalog(items, products)
    return {
        "items": sort_products(items),
        "stock_ok": stock_ok,
        "insight_pending": False,
    }


def build_insight_only() -> dict[str, Any]:
    """AI lines that are not already on HQ ICLOW. Waits for the background scan."""
    rows = fetch_to_order_rows()
    policies = load_insight_policies()
    iclow_bcodes = {str(row.get("bcode") or "").strip() for row in rows if row.get("bcode")}
    if not policies:
        return {"items": []}
    try:
        incoming = fetch_incoming_qty()
    except Exception:
        logger.warning("hq po incoming qty read failed", exc_info=True)
        return {"items": []}
    lines = _ensure_insight_future(policies, iclow_bcodes, incoming).result()
    _attach_parts9(lines)
    attach_catalog(lines)
    return {"items": lines}
