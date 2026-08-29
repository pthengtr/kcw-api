from __future__ import annotations

from typing import Any
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings


class TransferWriteError(RuntimeError):
    """Raised when transfer writing fails."""
    
    def __init__(self, message: str, *, code: str = "transfer_write_failed"):
        super().__init__(message)
        self.code = code


def _next_billno(conn, prefix: str, when) -> str:
    """Generate next bill number with YYMM prefix - like sa_writer.py pattern."""
    # Use the standard date-time formatter from sa_writer
    import datetime
    yymm = when.strftime("%y%m")
    stem = f"{prefix}{yymm}-"
    row = conn.execute(
        text(
            """
            SELECT MAX(BILLNO) AS max_no
            FROM dbo.SIMAS
            WHERE BILLNO LIKE :pat
            """
        ),
        {"pat": stem + "%"},
    ).mappings().first()
    max_no = (row or {}).get("max_no") or ""
    seq = 1
    if max_no and "-" in str(max_no):
        tail = str(max_no).rsplit("-", 1)[-1]
        try:
            seq = int(tail) + 1
        except ValueError:
            seq = 1
    
    candidate = f"{stem}{seq:05d}"
    if len(candidate) > 15:
        # Fall back to shorter sequence width
        candidate = f"{stem}{seq:04d}"
    if len(candidate) > 15:
        raise TransferWriteError("generated BILLNO exceeds 15 chars", code="billno_overflow")
    
    return candidate


def _get_hq_engine() -> Engine:
    """Get engine connected to HQ database for transfer operations."""
    # Use the configured writer credentials from transfer settings,
    # if available, otherwise use standard connection
    settings = get_transfer_settings()
    engine = get_site_engine("hq")
    return engine


def _get_syp_engine() -> Engine:
    """Get engine connected to SYP database for transfer operations."""
    engine = get_site_engine("syp")
    return engine


def _writer_engine_hq() -> Engine:
    """Get engine for writing to HQ (using writer credentials)."""
    return _get_hq_engine()