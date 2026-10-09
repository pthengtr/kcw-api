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
    if "permission was denied" in msg and "ICLOW" in msg:
        return HqPoError(
            "iclow_permission_denied",
            "python_writer ยังไม่มีสิทธิ์เขียน dbo.ICLOW บน KSS — "
            "รัน scripts/sql/grant_hq_po_writer.sql ด้วย SQL admin",
        )
    return None


def _clip(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _product(conn, bcode: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT TOP 1
              LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
              LTRIM(RTRIM(COALESCE(MCODE, ''))) AS MCODE,
              LTRIM(RTRIM(COALESCE(PCODE, ''))) AS PCODE,
              LTRIM(RTRIM(COALESCE(DESCR, ''))) AS DESCR,
              LTRIM(RTRIM(COALESCE(MODEL, ''))) AS MODEL,
              LTRIM(RTRIM(COALESCE(BRAND, ''))) AS BRAND,
              MAIN, SUB, PART, STATUS,
              LTRIM(RTRIM(COALESCE(SERIAL, ''))) AS SERIAL,
              LTRIM(RTRIM(COALESCE(EXMPT, ''))) AS EXMPT,
              LTRIM(RTRIM(COALESCE(LOCATION1, ''))) AS LOCATION1,
              QTYOH2,
              LTRIM(RTRIM(COALESCE(UI1, ''))) AS UI1,
              MTP2,
              PRICE1
            FROM dbo.ICMAS
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
            """
        ),
        {"bcode": bcode},
    ).mappings().first()
    return dict(row) if row else {}


def insert_ordered_lines(
    lines: list[dict[str, Any]], *, docno: str, on: date | None = None
) -> list[dict[str, Any]]:
    """Insert one already-ordered ICLOW row per AI line. Returns the lines with new ids."""
    if not lines:
        return []
    doc = (docno or "").strip()
    if not doc:
        raise HqPoError("bad_docno", "ไม่มีเลขที่ใบสั่งซื้อ")
    today = on or date.today()
    stored: list[dict[str, Any]] = []
    try:
        engine = _engine()
        with engine.begin() as conn:
            for line in lines:
                bcode = _clip(line.get("bcode"), 20)
                if not bcode:
                    raise HqPoError("not_confirmable", "ไม่มีรหัสสินค้า")
                vendor = _clip(line.get("vendor"), 10)
                if not vendor:
                    raise HqPoError("vendor_mismatch", f"{bcode} ไม่มีเจ้าหนี้")
                qty = _num(line.get("qty")) or 0.0
                if qty <= 0:
                    raise HqPoError("bad_qty", f"{bcode} จำนวนไม่ถูกต้อง")
                product = _product(conn, bcode)
                price = _num(product.get("PRICE1"))
                mtp = _num(product.get("MTP2")) or _num(line.get("mtp2")) or 1.0
                if mtp <= 0:
                    mtp = 1.0
                ui = _clip(line.get("ui") or product.get("UI1"), 10)
                descr = _clip(line.get("descr") or product.get("DESCR"), 60)
                params = {
                    "bcode": bcode,
                    "mcode": _clip(product.get("MCODE") or line.get("mcode"), 15),
                    "pcode": _clip(product.get("PCODE"), 15),
                    "descr": descr,
                    "model": _clip(product.get("MODEL"), 25),
                    "brand": _clip(product.get("BRAND"), 25),
                    "vendor": vendor,
                    "main": product.get("MAIN"),
                    "sub": product.get("SUB"),
                    "part": product.get("PART"),
                    "status": product.get("STATUS"),
                    "serial": _clip(product.get("SERIAL") or "N", 1) or "N",
                    "exmpt": _clip(product.get("EXMPT") or "N", 1) or "N",
                    "location1": _clip(product.get("LOCATION1"), 10),
                    "qtyoh": _num(product.get("QTYOH2")),
                    "qty": qty,
                    "ui": ui,
                    "mtp": mtp,
                    "price": price,
                    "amount": (price * qty) if price is not None else None,
                    "docdate": today,
                    "docno": _clip(doc, 15),
                }
                iclow_id = conn.execute(
                    text(
                        """
                        INSERT INTO dbo.ICLOW (
                          JOURMODE, BILLDATE, BCODE, MCODE, PCODE, DESCR, MODEL, BRAND,
                          VENDOR, MAIN, SUB, PART, STATUS, SERIAL, EXMPT, LOCATION1,
                          QTYOH, QTY, UI, MTP, PRICE, AMOUNT,
                          ORDERED, DOCDATE, DOCNO, RECEIVED, CANCELED, DONE
                        )
                        OUTPUT INSERTED.ID
                        VALUES (
                          '1', :docdate, :bcode, :mcode, :pcode, :descr, :model, :brand,
                          :vendor, :main, :sub, :part, :status, :serial, :exmpt, :location1,
                          :qtyoh, :qty, :ui, :mtp, :price, :amount,
                          'Y', :docdate, :docno, 'N', 'N', 'N'
                        )
                        """
                    ),
                    params,
                ).scalar()
                if not iclow_id:
                    raise HqPoError("iclow_insert_failed", f"เพิ่มแถว ICLOW ของ {bcode} ไม่สำเร็จ")
                saved = dict(line)
                saved["iclow_id"] = int(iclow_id)
                saved["bcode"] = bcode
                saved["vendor"] = vendor
                saved["qty"] = qty
                saved["descr"] = descr or None
                saved["ui"] = ui or None
                stored.append(saved)
    except HqPoError:
        raise
    except Exception as exc:
        denied = _permission(exc)
        if denied:
            raise denied from exc
        raise HqPoError("iclow_insert_failed", str(exc)) from exc
    return stored


def cancel_created(lines: list[dict[str, Any]], *, docno: str) -> None:
    """Mark rows this app inserted as canceled. They must not fall back onto รอสั่งซื้อ."""
    doc = (docno or "").strip()
    if not doc:
        raise HqPoError("bad_docno", "ไม่มีเลขที่ใบสั่งซื้อ")
    if not lines:
        return
    try:
        engine = _engine()
        with engine.begin() as conn:
            for line in lines:
                result = conn.execute(
                    text(
                        f"""
                        UPDATE dbo.ICLOW
                        SET CANCELED = 'Y'
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
                            DOCDATE = :docdate,
                            QTY = :qty,
                            AMOUNT = CASE WHEN PRICE IS NULL THEN AMOUNT ELSE PRICE * :qty END
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
                        "qty": float(line["qty"]),
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
