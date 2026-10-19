"""Open an HQ ICLOW รอสั่ง row when a KSS transfer-out drops on-hand to low stock.

PARTS9 does not do this from a trigger. The desktop app inserts ICLOW while it
posts the bill. The transfer writer updates QTYOH2 directly, so the ship path
has to insert the same waiting row.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

_NOT_CANCELED = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'"
_NOT_RECEIVED = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'"


def low_stock_reorder_qty(*, qtyget: Any, qtymin: Any, qtyoh: Any) -> float | None:
    """Order qty for a new waiting row, or None when this on-hand is not below qtylo.

    PARTS9 calls this field qtylo. On ICMAS it is QTYMIN.
    qtylo -1 (any QTYMIN < 0) means do not order. qtylo 0 is not a reorder point.
    A waiting row is opened only when on-hand is strictly below a positive qtylo.
    The row qty is QTYGET when that lot is set, otherwise the gap up to qtylo.
    """
    minimum = _num(qtymin)
    if minimum is None or minimum <= 0:
        return None
    on_hand = _num(qtyoh) or 0.0
    if on_hand >= minimum:
        return None
    lot = _num(qtyget) or 0.0
    if lot > 0:
        return lot
    return minimum - on_hand


def ensure_hq_low_stock_iclow(
    conn, *, bcode: str, qtyoh: float, on: date | None = None
) -> int | None:
    """Insert one ORDERED='N' ICLOW row when HQ on-hand is below qtylo and nothing is open.

    Returns the new ICLOW.ID, or None when qtylo is 0 or -1, on-hand is not below
    it, or an unreceived ICLOW row already exists.
    """
    code = (bcode or "").strip()
    if not code:
        return None
    product = _product(conn, code)
    if not product:
        return None
    qty = low_stock_reorder_qty(
        qtyget=product.get("QTYGET"),
        qtymin=product.get("QTYMIN"),
        qtyoh=qtyoh,
    )
    if qty is None:
        return None
    if _open_iclow_id(conn, code) is not None:
        return None
    product["BCODE"] = code
    return _insert_waiting_row(conn, product, qtyoh=qtyoh, qty=qty, on=on or date.today())


def backfill_hq_low_stock_iclow(conn, *, on: date | None = None) -> dict[str, int]:
    """Insert waiting ICLOW rows for every KSS product already below a positive qtylo."""
    today = on or date.today()
    open_codes = {
        str(code or "").strip()
        for code in conn.execute(
            text(
                f"""
                SELECT DISTINCT LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode
                FROM dbo.ICLOW
                WHERE {_NOT_CANCELED}
                  AND {_NOT_RECEIVED}
                """
            )
        ).scalars()
        if str(code or "").strip()
    }
    rows = conn.execute(
        text(
            """
            SELECT
              LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
              MCODE, PCODE, DESCR, MODEL, BRAND, OEM, VENDOR,
              MAIN, SUB, PART, STATUS, SERIAL, EXMPT, LOCATION1, LOCATION2,
              QTYMIN, QTYGET, QTYOH2, UI1, COSTLAST, COSTNET
            FROM dbo.ICMAS
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
              AND QTYMIN > 0
              AND QTYOH2 < QTYMIN
            """
        )
    ).mappings().all()
    inserted = 0
    skipped = 0
    for row in rows:
        product = dict(row)
        code = str(product.get("BCODE") or "").strip()
        if not code or code in open_codes:
            skipped += 1
            continue
        qtyoh = _num(product.get("QTYOH2")) or 0.0
        qty = low_stock_reorder_qty(
            qtyget=product.get("QTYGET"),
            qtymin=product.get("QTYMIN"),
            qtyoh=qtyoh,
        )
        if qty is None:
            skipped += 1
            continue
        iclow_id = _insert_waiting_row(conn, product, qtyoh=qtyoh, qty=qty, on=today)
        if iclow_id:
            open_codes.add(code)
            inserted += 1
        else:
            skipped += 1
    return {"candidates": len(rows), "inserted": inserted, "skipped": skipped}


def _insert_waiting_row(
    conn, product: dict[str, Any], *, qtyoh: float, qty: float, on: date
) -> int | None:
    code = str(product.get("BCODE") or "").strip()[:20]
    price = _num(product.get("COSTLAST"))
    if price is None:
        price = _num(product.get("COSTNET"))
    params = {
        "billdate": on,
        "bcode": code,
        "mcode": _clip(product.get("MCODE"), 15),
        "pcode": _clip(product.get("PCODE"), 15),
        "descr": _clip(product.get("DESCR"), 60),
        "model": _clip(product.get("MODEL"), 25),
        "brand": _clip(product.get("BRAND"), 25),
        "oem": _clip(product.get("OEM"), 15),
        "vendor": _clip(product.get("VENDOR"), 10),
        "main": _small(product.get("MAIN")),
        "sub": _small(product.get("SUB")),
        "part": _small(product.get("PART")),
        "status": _small(product.get("STATUS")),
        "serial": _flag(product.get("SERIAL")),
        "taxic": "N",
        "exmpt": _flag(product.get("EXMPT")),
        "location1": _clip(product.get("LOCATION1"), 10),
        "location2": _clip(product.get("LOCATION2"), 10),
        "qtyoh": float(qtyoh),
        "qty": qty,
        "ui": _clip(product.get("UI1"), 10),
        "mtp": 1.0,
        "price": price,
        "amount": (price * qty) if price is not None else None,
    }
    iclow_id = conn.execute(
        text(
            """
            INSERT INTO dbo.ICLOW (
              JOURMODE, BILLDATE, BCODE, MCODE, PCODE, DESCR, MODEL, BRAND, OEM,
              VENDOR, MAIN, SUB, PART, STATUS, SERIAL, TAXIC, EXMPT, LOCATION1, LOCATION2,
              QTYOH, QTY, UI, MTP, PRICE, AMOUNT,
              ORDERED, RECEIVED, CANCELED, DONE
            )
            OUTPUT INSERTED.ID
            VALUES (
              '1', :billdate, :bcode, :mcode, :pcode, :descr, :model, :brand, :oem,
              :vendor, :main, :sub, :part, :status, :serial, :taxic, :exmpt, :location1, :location2,
              :qtyoh, :qty, :ui, :mtp, :price, :amount,
              'N', 'N', 'N', 'N'
            )
            """
        ),
        params,
    ).scalar()
    return int(iclow_id) if iclow_id else None


def _product(conn, bcode: str) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT TOP 1
              LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
              MCODE, PCODE, DESCR, MODEL, BRAND, OEM, VENDOR,
              MAIN, SUB, PART, STATUS, SERIAL, EXMPT, LOCATION1, LOCATION2,
              QTYMIN, QTYGET, UI1, COSTLAST, COSTNET
            FROM dbo.ICMAS
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
            """
        ),
        {"bcode": bcode},
    ).mappings().first()
    return dict(row) if row else None


def _open_iclow_id(conn, bcode: str) -> int | None:
    """Unreceived, not-canceled row: already รอสั่ง or ค้างรับ."""
    found = conn.execute(
        text(
            f"""
            SELECT TOP 1 ID
            FROM dbo.ICLOW
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
              AND {_NOT_CANCELED}
              AND {_NOT_RECEIVED}
            """
        ),
        {"bcode": bcode},
    ).scalar()
    return int(found) if found else None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clip(value: Any, limit: int) -> str | None:
    text_value = str(value or "").strip()
    if not text_value:
        return None
    return text_value[:limit]


def _flag(value: Any) -> str:
    text_value = str(value or "").strip()
    return (text_value[:1] or "N")


def _small(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
