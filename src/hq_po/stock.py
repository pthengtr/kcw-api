"""HQ + SYP on-hand for safe-stock advice. Reuses the transfer ICMAS readers."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

_REFRESH_CHUNK = 200
# A reload while the list is already fresh should paint without another ledger scan.
_FRESH_SEC = 120.0
_fresh_lock = threading.Lock()
_fresh_until: dict[str, float] = {}


def parts9_order_qty(*, qtyget: Any, qtymin: Any, qtyoh: Any) -> float | None:
    """PARTS9 reorder qty: QTYGET when set, otherwise the gap up to QTYMIN.

    QTYMIN < 0 means do not restock.
    """
    try:
        minimum = float(qtymin) if qtymin not in (None, "") else None
    except (TypeError, ValueError):
        minimum = None
    if minimum is not None and minimum < 0:
        return None
    try:
        lot = float(qtyget or 0)
    except (TypeError, ValueError):
        lot = 0.0
    if lot > 0:
        return lot
    if minimum is None:
        return None
    try:
        on_hand = float(qtyoh or 0)
    except (TypeError, ValueError):
        on_hand = 0.0
    gap = minimum - on_hand
    if gap > 0:
        return gap
    return None


def _codes(bcodes: list[str]) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def refresh_qtyoh2(bcodes: list[str], *, sites: tuple[str, ...] = ("hq", "syp")) -> None:
    """Rebuild ICMAS.QTYOH2 from the product ledger before this service reads it.

    Same writer path as parts9 explorer product open and stock-check take.
    A failed or disabled sync leaves the later ICMAS read unchanged.
    """
    codes = _codes(bcodes)
    if not codes:
        return
    now = time.monotonic()
    with _fresh_lock:
        codes = [code for code in codes if _fresh_until.get(code, 0.0) <= now]
    if not codes:
        return
    try:
        from src.db.qtyoh2_ledger import (
            qtyoh2_sync_on_read_enabled,
            sync_qtyoh2_from_ledger_many,
        )
        from src.parts9_explorer.db import get_site_writer_engine
    except Exception:
        logger.warning("hq po qtyoh2 sync import failed", exc_info=True)
        return
    if not qtyoh2_sync_on_read_enabled():
        return

    def _site(site: str) -> set[str] | None:
        try:
            writer = get_site_writer_engine(site)
        except Exception:
            logger.warning("hq po qtyoh2 writer unavailable for %s", site, exc_info=True)
            return None
        if writer is None:
            return None
        fresh: set[str] = set()
        for start in range(0, len(codes), _REFRESH_CHUNK):
            results = sync_qtyoh2_from_ledger_many(
                codes[start : start + _REFRESH_CHUNK], engine=writer
            )
            fresh.update(result.bcode for result in results if not result.skipped)
        return fresh

    chosen = tuple(site for site in sites if site in ("hq", "syp"))
    if not chosen:
        return
    try:
        with ThreadPoolExecutor(max_workers=len(chosen)) as pool:
            synced = list(pool.map(_site, chosen))
    except Exception:
        logger.warning("hq po qtyoh2 sync failed", exc_info=True)
        return
    if any(site_codes is None for site_codes in synced):
        return
    fresh = set.intersection(*(site_codes or set() for site_codes in synced))
    if not fresh:
        return
    until = time.monotonic() + _FRESH_SEC
    with _fresh_lock:
        for code in fresh:
            _fresh_until[code] = until


def fetch_parts9_qty(bcodes: list[str]) -> dict[str, float]:
    """HQ ICMAS reorder qty keyed by product code."""
    codes = _codes(bcodes)
    if not codes:
        return {}
    from sqlalchemy import text

    from src.parts9_explorer.db import get_site_engine

    engine = get_site_engine("hq")
    out: dict[str, float] = {}
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"b{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":b{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT
                  LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
                  QTYGET, QTYMIN, QTYOH2
                FROM dbo.ICMAS
                WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                bcode = str(row.get("BCODE") or "").strip()
                qty = parts9_order_qty(
                    qtyget=row.get("QTYGET"),
                    qtymin=row.get("QTYMIN"),
                    qtyoh=row.get("QTYOH2"),
                )
                if bcode and qty:
                    out[bcode] = qty
    return out


def fetch_dual_stock(
    bcodes: list[str], *, refresh: bool = False
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], bool]:
    """Return (hq, syp, ok). ok is False when either site could not be read.

    refresh rebuilds QTYOH2 from the ledger first. Use it for the lines on screen
    and for a confirm. The full insight scan stays a read so it does not rewrite
    every policy SKU.
    """
    codes = _codes(bcodes)
    if not codes:
        return {}, {}, True
    if refresh:
        refresh_qtyoh2(codes)
    try:
        from src.transfer.parts9 import _fetch_icmas_chunked
    except Exception:
        logger.warning("hq po stock import failed", exc_info=True)
        return {}, {}, False
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            hq_fut = pool.submit(_fetch_icmas_chunked, "hq", codes)
            syp_fut = pool.submit(_fetch_icmas_chunked, "syp", codes)
            hq = hq_fut.result()
            syp = syp_fut.result()
    except Exception:
        logger.warning("hq po dual stock read failed", exc_info=True)
        return {}, {}, False
    return hq, syp, True
