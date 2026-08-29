from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings


class ICLOWStampError(RuntimeError):
    """Raised when stamping ICLOW fails."""

    def __init__(self, message: str, *, code: str = "iclow_stamp_failed"):
        super().__init__(message)
        self.code = code


def _get_iclow_engine() -> Engine:
    """Get engine connected to SYP database for ICLOW operations."""
    settings = get_transfer_settings()
    if not settings.is_syp:
        raise ICLOWStampError("ICLOW stamping is SYP-only", code="not_syp_site")
    
    # Use the configured database name and server 
    engine = get_site_engine("syp")
    return engine


def stamp_on_submit(*, bcode: str, short_id: str) -> dict[str, Any] | None:
    """Stamp ICLOW on submit. Returns None if no open row (app transfer still valid)."""
    engine = _get_iclow_engine()
    docno = f"TRF-{short_id}"[:40]

    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1 ID
                    FROM dbo.ICLOW
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) = 'N'
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) = 'N'
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
                    ORDER BY DOCDATE DESC, ID DESC
                    """
                ),
                {"bcode": bcode.strip()},
            ).mappings().first()

            if not row:
                return None

            iclow_id = row["ID"]

            conn.execute(
                text(
                    """
                    UPDATE dbo.ICLOW
                    SET ORDERED = 'Y',
                        DOCNO = :docno,
                        DOCDATE = :docdate
                    WHERE ID = :iclow_id
                    """
                ),
                {
                    "iclow_id": iclow_id,
                    "docno": docno,
                    "docdate": date.today(),
                },
            )

            return {"iclow_id": iclow_id, "bcode": bcode}
            
    except Exception as exc:
        # Re-raise our custom error if it's already an ICLOWStampError
        if isinstance(exc, ICLOWStampError):
            raise
        # Otherwise wrap it in an ICLOWStampError
        raise ICLOWStampError(str(exc), code="iclow_update_failed") from exc


def revert_on_cancel(*, iclow_id: str) -> None:
    """Revert ICLOW stamp on cancel - set ORDERED=N, DOCNO cleared."""
    engine = _get_iclow_engine()
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE dbo.ICLOW
                    SET ORDERED = 'N',
                        DOCNO = '',
                        DOCDATE = NULL
                    WHERE ID = :iclow_id
                    """
                ),
                {"iclow_id": iclow_id},
            )
    except Exception as exc:
        # Re-raise our custom error if it's already an ICLOWStampError
        if isinstance(exc, ICLOWStampError):
            raise
        # Otherwise wrap it in an ICLOWStampError
        raise ICLOWStampError(str(exc), code="iclow_revert_failed") from exc


def mark_received(*, iclow_id: str, tf_billno: str) -> None:
    """Mark ICLOW record as received - set RECEIVED=Y, RCVDNO=left12(tf_billno), RCVDDATE=today."""
    engine = _get_iclow_engine()
    
    try:
        with engine.begin() as conn:
            # Extract left 12 characters of tf_billno
            rcvdno = tf_billno.strip()[:12] if tf_billno else ""
            
            conn.execute(
                text(
                    """
                    UPDATE dbo.ICLOW
                    SET RECEIVED = 'Y',
                        RCVDNO = :rcvdno,
                        RCVDDATE = :rcvddate
                    WHERE ID = :iclow_id
                    """
                ),
                {
                    "iclow_id": iclow_id,
                    "rcvdno": rcvdno,
                    "rcvddate": date.today(),
                },
            )
    except Exception as exc:
        # Re-raise our custom error if it's already an ICLOWStampError
        if isinstance(exc, ICLOWStampError):
            raise
        # Otherwise wrap it in an ICLOWStampError
        raise ICLOWStampError(str(exc), code="iclow_receive_failed") from exc