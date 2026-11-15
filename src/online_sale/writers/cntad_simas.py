from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.online_sale.docno import cntad_prefix, format_cntad
from src.online_sale.errors import OnlineSaleError
from src.online_sale.vat import money, totals_from_amounts
from src.transfer.writers._engine import (
    _fetch_icmas_row,
    transfer_write_permission_hint,
    writer_engine_for_branch,
)


def _next_cntad_billno(conn, when: datetime) -> str:
    stem = cntad_prefix(when)
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
    billno = format_cntad(seq, when)
    if len(billno) > 15:
        raise OnlineSaleError("billno", "เลข CNTAD ยาวเกิน 15 ตัวอักษร")
    return billno


def post_cntad(
    *,
    tad_billno: str,
    acctno: str,
    acctname: str,
    remarks: str,
    operator: str,
    lines: list[dict[str, Any]],
    reason: str = "",
) -> dict[str, Any]:
    if not lines:
        raise OnlineSaleError("lines", "เลือกสินค้าที่ต้องการคืนอย่างน้อย 1 รายการ")
    tad = (tad_billno or "").strip().upper()
    if not tad.startswith("TAD"):
        raise OnlineSaleError("tad", "อ้างอิงได้เฉพาะบิล TAD")

    engine = writer_engine_for_branch("HQ")
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:02d}{now.minute:02d}"
    jourmode = "1"
    billtype = "2"
    bookno = "7"

    amounts: list = []
    prepared: list[dict[str, Any]] = []
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        qty = abs(float(raw.get("qty") or 0))
        price = money(raw.get("price"))
        if not bcode or qty <= 0 or price <= 0:
            raise OnlineSaleError("lines", "รายการคืนไม่ครบ (รหัส/จำนวน/ราคา)")
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
    # Credit note stores negative money totals
    pos_totals = totals_from_amounts(amounts)
    beforetax = -pos_totals["beforetax"]
    tax = -pos_totals["tax"]
    aftertax = -pos_totals["aftertax"]

    try:
        with engine.begin() as conn:
            billno = _next_cntad_billno(conn, now)
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
                    "beforetax": float(beforetax),
                    "tax": float(tax),
                    "aftertax": float(aftertax),
                    "dueamt": float(aftertax),
                    "acctno": acctno[:15],
                    "acctname": (acctname or "")[:60],
                    "po": tad[:15],
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
                  :qty, :ui, 1, :price, 0, 0, :amount,
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
                on_hand = float(product.get("QTYOH2") or 0)
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
                        "qty": -line["qty"],
                        "ui": line["ui"] or str(product.get("UI1") or "หน่วย")[:10],
                        "price": float(line["price"]),
                        "amount": -float(line["amount"]),
                    },
                )
                conn.execute(
                    qtyoh2_update,
                    {"qty": on_hand + line["qty"], "bcode": line["bcode"]},
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
        "tad_billno": tad,
        "bill_date": billdate.date().isoformat(),
        "bill_time": billtime,
        "beforetax": float(beforetax),
        "tax": float(tax),
        "aftertax": float(aftertax),
        "reason": reason,
        "lines": len(prepared),
    }
