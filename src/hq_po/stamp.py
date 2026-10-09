"""Stamp HQ ICLOW ordered / undo that stamp. Never writes RECEIVED."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from src.hq_po.guards import HqPoError

_ORDERED_N = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) <> 'Y'"
_RECEIVED_N = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'"
_NOT_CANCELED = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'"


def _engine():
    from src.transfer.writers._engine import writer_engine_for_branch

    return writer_engine_for_branch("hq")


def _permission(exc: Exception) -> HqPoError | None:
    msg = str(exc)
    if "UPDATE permission was denied" in msg and "ICLOW" in msg:
        return HqPoError(
            "iclow_permission_denied",
            "python_writer ยังไม่มีสิทธิ์ UPDATE dbo.ICLOW บน KSS — "
            "รัน scripts/sql/grant_hq_po_writer.sql ด้วย SQL admin",
        )
    return None


def stamp_ordered(lines: list[dict[str, Any]], *, docno: str, on: date | None = None) -> None:
    """Set ORDERED, DOCNO, DOCDATE on the given ICLOW ids. One transaction."""
    if not lines:
        raise HqPoError("empty", "ไม่มีแถวให้สั่ง")
    doc = (docno or "").strip()
    if not doc:
        raise HqPoError("bad_docno", "ไม่มีเลขที่ใบสั่งซื้อ")
    today = on or date.today()
    try:
        engine = _engine()
        with engine.begin() as conn:
            for line in lines:
                result = conn.execute(
                    text(
                        f"""
                        UPDATE dbo.ICLOW
                        SET ORDERED = 'Y',
                            DOCNO = :docno,
                            DOCDATE = :docdate
                        WHERE CONVERT(bigint, ID) = :iclow_id
                          AND {_ORDERED_N}
                          AND {_RECEIVED_N}
                          AND {_NOT_CANCELED}
                        """
                    ),
                    {
                        "iclow_id": int(line["iclow_id"]),
                        "docno": doc[:40],
                        "docdate": today,
                    },
                )
                if result.rowcount != 1:
                    bcode = line.get("bcode") or line["iclow_id"]
                    raise HqPoError("stamp_conflict", f"สั่ง {bcode} ไม่ได้ เพราะแถว ICLOW เปลี่ยนไปแล้ว")
    except HqPoError:
        raise
    except Exception as exc:
        denied = _permission(exc)
        if denied:
            raise denied from exc
        raise HqPoError("iclow_update_failed", str(exc)) from exc


def revert_ordered(lines: list[dict[str, Any]], *, docno: str) -> None:
    """Clear our ORDERED stamp. Refuses rows PIMAS already received or that no longer carry our DOCNO."""
    doc = (docno or "").strip()
    if not doc:
        raise HqPoError("bad_docno", "ไม่มีเลขที่ใบสั่งซื้อ")
    try:
        engine = _engine()
        with engine.begin() as conn:
            for line in lines:
                result = conn.execute(
                    text(
                        f"""
                        UPDATE dbo.ICLOW
                        SET ORDERED = 'N',
                            DOCNO = '',
                            DOCDATE = NULL
                        WHERE CONVERT(bigint, ID) = :iclow_id
                          AND LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(DOCNO,'')))) = :docno
                          AND {_RECEIVED_N}
                        """
                    ),
                    {"iclow_id": int(line["iclow_id"]), "docno": doc},
                )
                if result.rowcount != 1:
                    bcode = line.get("bcode") or line["iclow_id"]
                    raise HqPoError(
                        "revert_conflict",
                        f"ยกเลิก {bcode} ไม่ได้ เพราะรับแล้วหรือ DOCNO ไม่ตรง",
                    )
    except HqPoError:
        raise
    except Exception as exc:
        denied = _permission(exc)
        if denied:
            raise denied from exc
        raise HqPoError("iclow_update_failed", str(exc)) from exc
