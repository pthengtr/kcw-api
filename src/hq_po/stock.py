"""HQ + SYP on-hand for safe-stock advice. Reuses the transfer ICMAS readers."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


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


def fetch_parts9_qty(bcodes: list[str]) -> dict[str, float]:
    """HQ ICMAS reorder qty keyed by product code."""
    codes = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
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


def fetch_dual_stock(bcodes: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], bool]:
    """Return (hq, syp, ok). ok is False when either site could not be read."""
    codes = [str(b).strip() for b in bcodes if str(b or "").strip()]
    if not codes:
        return {}, {}, True
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
