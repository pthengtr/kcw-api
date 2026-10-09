"""HQ + SYP on-hand for safe-stock advice. Reuses the transfer ICMAS readers."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


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
