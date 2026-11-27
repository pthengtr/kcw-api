from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.online_sale.docno import format_tad, tad_prefix
from src.online_sale.errors import OnlineSaleError
from src.online_sale.shops import detect_platform, validate_online_po
from src.online_sale.vat import money, totals_from_amounts
from src.transfer.writers._engine import (
    _fetch_icmas_row,
    transfer_write_permission_hint,
    writer_engine_for_branch,
)


def _line_mtp(product: dict[str, Any], ui: str) -> float:
    """Match POS: UI2 uses ICMAS.MTP2; UI1 (or unknown) uses 1."""
    chosen = (ui or "").strip()
    ui2 = str(product.get("UI2") or "").strip()
    try:
        mtp2 = float(product.get("MTP2") or 1) or 1.0
    except (TypeError, ValueError):
        mtp2 = 1.0
    if chosen and ui2 and chosen == ui2 and mtp2 > 1:
        return mtp2
    return 1.0


def _stock_units(qty: float, mtp: float) -> float:
    factor = float(mtp or 0)
    if factor <= 0:
        factor = 1.0
    return abs(float(qty or 0)) * factor


def _next_tad_billno(conn, when: datetime) -> str:
    stem = tad_prefix(when)
    row = conn.execute(
        text(
            """
            SELECT MAX(
              TRY_CAST(
                SUBSTRING(
                  LTRIM(RTRIM(CONVERT(nvarchar(40), BILLNO))),
                  LEN(:stem) + 1,
                  40
                ) AS int
              )
            ) AS max_seq
            FROM dbo.SIMAS WITH (UPDLOCK, HOLDLOCK)
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BILLNO))) LIKE :pat
            """
        ),
        {"pat": stem + "%", "stem": stem},
    ).mappings().first()
    max_seq = (row or {}).get("max_seq")
    try:
        seq = int(max_seq) + 1 if max_seq is not None else 1
    except (TypeError, ValueError):
        seq = 1
    billno = format_tad(seq, when)
    if len(billno) > 15:
        raise OnlineSaleError("billno", "เลข TAD ยาวเกิน 15 ตัวอักษร")
    return billno


def post_tad(
    *,
    acctno: str,
    acctname: str,
    online_po: str,
    remarks: str,
    operator: str,
    lines: list[dict[str, Any]],
    allow_oversell: bool = False,
) -> dict[str, Any]:
    if not lines:
        raise OnlineSaleError("lines", "เพิ่มอย่างน้อย 1 รายการสินค้า")
    platform = detect_platform(acctname, acctno)
    po = validate_online_po(platform, online_po)

    engine = writer_engine_for_branch("HQ")
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:02d}{now.minute:02d}"
    jourmode = "1"
    billtype = "1"
    bookno = "2"

    amounts = []
    prepared: list[dict[str, Any]] = []
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        qty = float(raw.get("qty") or 0)
        price = money(raw.get("price"))
        if not bcode:
            raise OnlineSaleError("lines", "มีรายการที่ไม่มีรหัสสินค้า")
        if qty <= 0:
            raise OnlineSaleError("lines", f"จำนวนของ {bcode} ต้องมากกว่า 0")
        if price <= 0:
            raise OnlineSaleError("lines", f"ราคาของ {bcode} ต้องมากกว่า 0")
        amount = money(Decimal(str(qty)) * price)
        amounts.append(amount)
        prepared.append(
            {
                "bcode": bcode,
                "qty": qty,
                "price": price,
                "amount": amount,
                "detail": str(raw.get("detail") or raw.get("descr") or "")[:60],
                "ui": str(raw.get("ui") or "หน่วย")[:10],
            }
        )
    totals = totals_from_amounts(amounts)
    aftertax = totals["aftertax"]

    try:
        with engine.begin() as conn:
            # Many TAD bills may share one online order number (soft warning in UI).
            billno = _next_tad_billno(conn, now)
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.SIMAS (
                      JOURMODE, JOURTYPE, JOURDATE, JOURTIME, DEPTNO, BOOKNO,
                      BILLTYPE, BILLDATE, BILLTIME, BILLNO, LINES, TAXIC,
                      DISCOUNT, DEDUCT, BEFORETAX, VAT, TAX, AFTERTAX, EXEMPT, SVCCHG,
                      PAID, CASHED, CASHAMT, CHKAMT, DUEAMT,
                      ACCTNO, ACCTNAME, PO,
                      SALE, REMARKS, POSTED1, POSTED2, CANCELED, DONE
                    ) VALUES (
                      :jourmode, 'SJ', :billdate, :jourtime, '1', :bookno,
                      :billtype, :billdate, :billtime, :billno, :lines, 'Y',
                      0, 0, :beforetax, 7, :tax, :aftertax, 0, 0,
                      'N', 'N', 0, 0, :dueamt,
                      :acctno, :acctname, :po,
                      :sale, :remarks, 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "bookno": bookno,
                    "billdate": billdate,
                    "jourtime": billtime,
                    "billtime": billtime,
                    "billtype": billtype,
                    "billno": billno,
                    "lines": len(prepared),
                    "beforetax": float(totals["beforetax"]),
                    "tax": float(totals["tax"]),
                    "aftertax": float(aftertax),
                    "dueamt": float(aftertax),
                    "acctno": acctno[:15],
                    "acctname": (acctname or "")[:60],
                    "po": po,  # text; SIMAS.PO is nvarchar(30)
                    "sale": (operator or "")[:15],
                    "remarks": (remarks or "")[:30],
                },
            )

            sidet_insert = text(
                """
                INSERT INTO dbo.SIDET (
                  JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
                  LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
                  STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
                  QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
                  PAID, DONE, CANCELED
                ) VALUES (
                  :jourmode, 'SJ', :billdate, :billtype, :billdate, :billno,
                  :line, 1, :bcode, :pcode, :mcode, :detail, 'Y', :location1,
                  1, 'N', 'Y', 'N', 'Y',
                  :qty, :ui, :mtp, :price, 0, 0, :amount,
                  'N', 'N', 'N'
                )
                """
            )
            qtyoh2_update = text(
                """
                UPDATE dbo.ICMAS SET QTYOH2 = :qty
                WHERE LTRIM(RTRIM(BCODE)) = :bcode
                """
            )

            for i, line in enumerate(prepared, start=1):
                product = _fetch_icmas_row(conn, line["bcode"])
                if not product:
                    raise OnlineSaleError("product", f"ไม่พบ BCODE {line['bcode']} ใน ICMAS")
                ui = (line["ui"] or str(product.get("UI1") or "หน่วย"))[:10]
                mtp = _line_mtp(product, ui)
                stock_qty = _stock_units(line["qty"], mtp)
                on_hand = float(product.get("QTYOH2") or 0)
                if not allow_oversell and on_hand < stock_qty:
                    raise OnlineSaleError(
                        "stock",
                        f"{line['bcode']} สต็อกคงเหลือ {on_hand:g} ไม่พอขาย {line['qty']:g} {ui}"
                        + (f" ({stock_qty:g} หน่วยย่อย)" if mtp > 1 else ""),
                    )
                detail = line["detail"] or str(product.get("DESCR") or "")[:60]
                conn.execute(
                    sidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": billno,
                        "line": i * 10,
                        "bcode": line["bcode"],
                        "pcode": product.get("PCODE") or None,
                        "mcode": product.get("MCODE") or None,
                        "detail": detail,
                        "location1": (str(product.get("LOCATION1") or "")[:10] or None),
                        "qty": line["qty"],
                        "ui": ui,
                        "mtp": mtp,
                        "price": float(line["price"]),
                        "amount": float(line["amount"]),
                    },
                )
                conn.execute(
                    qtyoh2_update,
                    {"qty": on_hand - stock_qty, "bcode": line["bcode"]},
                )
    except OnlineSaleError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(
            exc, branch="HQ", tables="SIMAS/SIDET/ICMAS"
        )
        if hint:
            raise OnlineSaleError("permission_denied", hint, status=502) from exc
        raise OnlineSaleError("sql_error", str(exc), status=502) from exc

    return {
        "billno": billno,
        "bill_date": billdate.date().isoformat(),
        "bill_time": billtime,
        "beforetax": float(totals["beforetax"]),
        "tax": float(totals["tax"]),
        "aftertax": float(aftertax),
        "online_po": po,
        "acctno": acctno,
        "lines": len(prepared),
    }


def _prepare_lines(lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Decimal]]:
    if not lines:
        raise OnlineSaleError("lines", "เพิ่มอย่างน้อย 1 รายการสินค้า")
    amounts: list[Decimal] = []
    prepared: list[dict[str, Any]] = []
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        qty = float(raw.get("qty") or 0)
        price = money(raw.get("price"))
        if not bcode:
            raise OnlineSaleError("lines", "มีรายการที่ไม่มีรหัสสินค้า")
        if qty <= 0:
            raise OnlineSaleError("lines", f"จำนวนของ {bcode} ต้องมากกว่า 0")
        if price <= 0:
            raise OnlineSaleError("lines", f"ราคาของ {bcode} ต้องมากกว่า 0")
        amount = money(Decimal(str(qty)) * price)
        amounts.append(amount)
        prepared.append(
            {
                "bcode": bcode,
                "qty": qty,
                "price": price,
                "amount": amount,
                "detail": str(raw.get("detail") or raw.get("descr") or "")[:60],
                "ui": str(raw.get("ui") or "หน่วย")[:10],
            }
        )
    return prepared, totals_from_amounts(amounts)


def update_tad(
    *,
    billno: str,
    acctno: str,
    acctname: str,
    online_po: str,
    remarks: str,
    operator: str,
    lines: list[dict[str, Any]],
    allow_oversell: bool = False,
) -> dict[str, Any]:
    exact = (billno or "").strip().upper()
    if not exact.startswith("TAD"):
        raise OnlineSaleError("bill", "แก้ไขได้เฉพาะบิล TAD")
    platform = detect_platform(acctname, acctno)
    po = validate_online_po(platform, online_po)

    prepared, totals = _prepare_lines(lines)
    aftertax = totals["aftertax"]
    engine = writer_engine_for_branch("HQ")
    now = datetime.now()
    billtime = f"{now.hour:02d}{now.minute:02d}"

    try:
        with engine.begin() as conn:
            header = conn.execute(
                text(
                    """
                    SELECT TOP 1
                      LTRIM(RTRIM(BILLNO)) AS billno,
                      BILLDATE AS bill_date,
                      COALESCE(CANCELED, 'N') AS canceled
                    FROM dbo.SIMAS WITH (UPDLOCK, HOLDLOCK)
                    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
                    """
                ),
                {"exact": exact},
            ).mappings().first()
            if not header:
                raise OnlineSaleError("bill", f"ไม่พบบิล {exact}", status=404)
            if str(header.get("canceled") or "N").strip().upper() == "Y":
                raise OnlineSaleError("bill", "บิลนี้ถูกยกเลิกแล้ว แก้ไขไม่ได้")
            billdate = header.get("bill_date") or now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            jourmode = "1"
            billtype = "1"

            old_lines = conn.execute(
                text(
                    """
                    SELECT
                      LINE AS line_no,
                      LTRIM(RTRIM(BCODE)) AS bcode,
                      QTY AS qty,
                      MTP AS mtp
                    FROM dbo.SIDET WITH (UPDLOCK, HOLDLOCK)
                    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
                      AND COALESCE(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"exact": exact},
            ).mappings().all()

            qtyoh2_update = text(
                """
                UPDATE dbo.ICMAS SET QTYOH2 = :qty
                WHERE LTRIM(RTRIM(BCODE)) = :bcode
                """
            )
            # Restore stock from previous lines, then soft-cancel them.
            for old in old_lines:
                bcode = str(old.get("bcode") or "").strip()
                qty = abs(float(old.get("qty") or 0))
                mtp = float(old.get("mtp") or 1) or 1.0
                stock_qty = _stock_units(qty, mtp)
                if not bcode or stock_qty <= 0:
                    continue
                product = _fetch_icmas_row(conn, bcode)
                if not product:
                    raise OnlineSaleError("product", f"ไม่พบ BCODE {bcode} ใน ICMAS")
                on_hand = float(product.get("QTYOH2") or 0)
                conn.execute(qtyoh2_update, {"qty": on_hand + stock_qty, "bcode": bcode})

            conn.execute(
                text(
                    """
                    UPDATE dbo.SIDET
                    SET CANCELED = 'Y'
                    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
                      AND COALESCE(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"exact": exact},
            )

            sidet_insert = text(
                """
                INSERT INTO dbo.SIDET (
                  JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
                  LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
                  STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
                  QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
                  PAID, DONE, CANCELED
                ) VALUES (
                  :jourmode, 'SJ', :billdate, :billtype, :billdate, :billno,
                  :line, 1, :bcode, :pcode, :mcode, :detail, 'Y', :location1,
                  1, 'N', 'Y', 'N', 'Y',
                  :qty, :ui, :mtp, :price, 0, 0, :amount,
                  'N', 'N', 'N'
                )
                """
            )

            for i, line in enumerate(prepared, start=1):
                product = _fetch_icmas_row(conn, line["bcode"])
                if not product:
                    raise OnlineSaleError("product", f"ไม่พบ BCODE {line['bcode']} ใน ICMAS")
                ui = (line["ui"] or str(product.get("UI1") or "หน่วย"))[:10]
                mtp = _line_mtp(product, ui)
                stock_qty = _stock_units(line["qty"], mtp)
                on_hand = float(product.get("QTYOH2") or 0)
                if not allow_oversell and on_hand < stock_qty:
                    raise OnlineSaleError(
                        "stock",
                        f"{line['bcode']} สต็อกคงเหลือ {on_hand:g} ไม่พอขาย {line['qty']:g} {ui}"
                        + (f" ({stock_qty:g} หน่วยย่อย)" if mtp > 1 else ""),
                    )
                detail = line["detail"] or str(product.get("DESCR") or "")[:60]
                conn.execute(
                    sidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": exact,
                        "line": i * 10,
                        "bcode": line["bcode"],
                        "pcode": product.get("PCODE") or None,
                        "mcode": product.get("MCODE") or None,
                        "detail": detail,
                        "location1": (str(product.get("LOCATION1") or "")[:10] or None),
                        "qty": line["qty"],
                        "ui": ui,
                        "mtp": mtp,
                        "price": float(line["price"]),
                        "amount": float(line["amount"]),
                    },
                )
                conn.execute(
                    qtyoh2_update,
                    {"qty": on_hand - stock_qty, "bcode": line["bcode"]},
                )

            # Keep original SALE (issuer LINE name). Edits must not rewrite
            # the salesperson snapshotted at issue time.
            conn.execute(
                text(
                    """
                    UPDATE dbo.SIMAS
                    SET ACCTNO = :acctno,
                        ACCTNAME = :acctname,
                        PO = :po,
                        REMARKS = :remarks,
                        LINES = :lines,
                        BEFORETAX = :beforetax,
                        TAX = :tax,
                        AFTERTAX = :aftertax,
                        DUEAMT = :dueamt,
                        BILLTIME = :billtime
                    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
                    """
                ),
                {
                    "exact": exact,
                    "acctno": acctno[:15],
                    "acctname": (acctname or "")[:60],
                    "po": po,  # text; SIMAS.PO is nvarchar(30)
                    "remarks": (remarks or "")[:30],
                    "lines": len(prepared),
                    "beforetax": float(totals["beforetax"]),
                    "tax": float(totals["tax"]),
                    "aftertax": float(aftertax),
                    "dueamt": float(aftertax),
                    "billtime": billtime,
                },
            )
    except OnlineSaleError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(
            exc, branch="HQ", tables="SIMAS/SIDET/ICMAS"
        )
        if hint:
            raise OnlineSaleError("permission_denied", hint, status=502) from exc
        raise OnlineSaleError("sql_error", str(exc), status=502) from exc

    return {
        "billno": exact,
        "bill_time": billtime,
        "beforetax": float(totals["beforetax"]),
        "tax": float(totals["tax"]),
        "aftertax": float(aftertax),
        "online_po": po,
        "acctno": acctno,
        "lines": len(prepared),
        "updated": True,
    }
