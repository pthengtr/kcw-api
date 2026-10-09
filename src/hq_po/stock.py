"""HQ + SYP on-hand for safe-stock advice. Reuses the transfer ICMAS readers."""

from __future__ import annotations

import logging
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
        hq = _fetch_icmas_chunked("hq", codes)
        syp = _fetch_icmas_chunked("syp", codes)
    except Exception:
        logger.warning("hq po dual stock read failed", exc_info=True)
        return {}, {}, False
    return hq, syp, True
