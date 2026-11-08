"""HQ PARTS9 purchase credit notes (KCCN / 7KCCN) from goods receive shortfalls."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from src.hq_receive.docno import cn_prefix, format_cn
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.rules import credit_note_lines
from src.transfer.writers._engine import _fetch_icmas_row

BOOKNO = "5"  # ลดหนี้ซื้อ
BILLTYPE = "2"  # purchase credit note


def receipt_is_vat(receipt: dict[str, Any]) -> bool:
    tax = float(receipt.get("tax") or 0)
    if tax > 0:
        return True
    vat = receipt.get("vat")
    if vat in (7, "7", 7.0, True, "Y", "y"):
        return True
    try:
        if float(vat or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def plan_credit_note(receipt: dict[str, Any], *, source_billno: str) -> dict[str, Any] | None:
    lines = credit_note_lines(receipt)
    if not lines:
        return None
    before = round(sum(float(ln.get("amount") or 0) for ln in lines), 2)
    is_vat = receipt_is_vat(receipt)
    tax = round(before * 0.07, 2) if is_vat else 0.0
    after = round(before + tax, 2)
    return {
        "source_pimas_billno": source_billno,
        "is_vat": is_vat,
        "prefix": cn_prefix(is_vat=is_vat),
        "beforetax": -before,
        "tax": -tax,
        "aftertax": -after,
        "lines": lines,
        "vendor_acctno": str(receipt.get("vendor_acctno") or "").strip(),
        "vendor_name": receipt.get("vendor_name") or "",
        "status": "awaiting_vendor_doc" if is_vat else "completed",
    }


def next_cn_billno(conn, *, is_vat: bool, when: datetime | date | None = None) -> str:
    when = when or datetime.now()
    prefix = cn_prefix(is_vat=is_vat, when=when)
    row = conn.execute(
        text(
            """
            SELECT MAX(LTRIM(RTRIM(BILLNO))) AS BILLNO
            FROM dbo.PIMAS WITH (UPDLOCK, HOLDLOCK)
            WHERE LTRIM(RTRIM(BILLNO)) LIKE :pfx
            """
        ),
        {"pfx": prefix + "%"},
    ).mappings().first()
    last = str((row or {}).get("BILLNO") or "").strip()
    seq = 0
    if last.startswith(prefix):
        tail = last[len(prefix) :]
        if tail.isdigit():
            seq = int(tail)
    return format_cn(seq + 1, is_vat=is_vat, when=when)


def insert_credit_note(
    conn,
    plan: dict[str, Any],
    *,
    operator: str,
    billdate: datetime,
    billtime: str,
) -> str:
    """Insert PIMAS/PIDET credit note and reduce ICMAS.QTYOH2. Returns cn billno."""
    acctno = str(plan.get("vendor_acctno") or "").strip()
    if not acctno:
        raise HqReceiveError("missing_vendor", "ยังไม่ได้เลือกเจ้าหนี้สำหรับใบลดหนี้")
    lines = plan.get("lines") or []
    if not lines:
        raise HqReceiveError("credit_note_empty", "ไม่มีรายการสำหรับใบลดหนี้")

    acctname = (plan.get("vendor_name") or "")[:60]
    if not acctname:
        row = conn.execute(
            text(
                """
                SELECT LTRIM(RTRIM(COALESCE(ACCTNAME,''))) AS ACCTNAME
                FROM dbo.APMAS WITH (NOLOCK)
                WHERE LTRIM(RTRIM(ACCTNO)) = :a
                """
            ),
            {"a": acctno},
        ).mappings().first()
        acctname = str((row or {}).get("ACCTNAME") or acctno)[:60]

    for line in lines:
        bcode = str(line.get("bcode") or "").strip()
        if not bcode or not _fetch_icmas_row(conn, bcode):
            raise HqReceiveError("missing_icmas", f"ไม่พบรหัส {bcode} ใน ICMAS (ใบลดหนี้)")

    is_vat = bool(plan.get("is_vat"))
    billno = next_cn_billno(conn, is_vat=is_vat, when=billdate)
    before = float(plan["beforetax"])  # already negative
    tax = float(plan["tax"])
    after = float(plan["aftertax"])
    source = str(plan.get("source_pimas_billno") or "")[:15]
    remarks = (str(billdate.strftime("%d/%m/%y"))[:30])
    jourmode = "1" if is_vat else "2"
    vat_flag = 7.0 if is_vat else 0.0

    conn.execute(
        text(
            """
            INSERT INTO dbo.PIMAS (
              JOURMODE, JOURTYPE, JOURDATE, JOURTIME, DEPTNO, BOOKNO,
              BILLTYPE, BILLDATE, BILLTIME, BILLNO, LINES, TAXIC,
              DISCOUNT, DEDUCT, BEFORETAX, VAT, TAX, AFTERTAX, EXEMPT, SVCCHG,
              PAID, CASHED, CASHAMT, CHKAMT, DUEAMT,
              ACCTNO, ACCTNAME, PO, SALE, RE, NOTENO, REMARKS,
              POSTED1, POSTED2, CANCELED, DONE
            ) VALUES (
              :jourmode, 'PJ', :billdate, :jourtime, '1', :bookno,
              :billtype, :billdate, :billtime, :billno, :lines, 'N',
              0, 0, :beforetax, :vat, :tax, :aftertax, 0, 0,
              'N', 'N', 0, 0, :dueamt,
              :acctno, :acctname, :po, :sale, :re, NULL, :remarks,
              'N', 'N', 'N', 'N'
            )
            """
        ),
        {
            "jourmode": jourmode,
            "bookno": BOOKNO,
            "billdate": billdate,
            "jourtime": billtime,
            "billtime": billtime,
            "billtype": BILLTYPE,
            "billno": billno,
            "lines": len(lines),
            "beforetax": before,
            "vat": vat_flag,
            "tax": tax,
            "aftertax": after,
            "dueamt": after,
            "acctno": acctno,
            "acctname": acctname,
            "po": source or None,
            "sale": (operator or "")[:15],
            "re": "ตัด30"[:10],
            "remarks": remarks,
        },
    )

    pidet_insert = text(
        """
        INSERT INTO dbo.PIDET (
          JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
          LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
          STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
          QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
          PAID, DONE, CANCELED
        ) VALUES (
          :jourmode, 'PJ', :billdate, :billtype, :billdate, :billno,
          :line, 1, :bcode, :pcode, :mcode, :detail, 'Y', :location1,
          1, 'N', 'N', 'N', :isvat,
          :qty, :ui, :mtp, :price, :xprice, :vat, :amount,
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

    for i, line in enumerate(lines, start=1):
        bcode = str(line.get("bcode") or "").strip()
        qty_pos = float(line.get("qty") or 0)
        cost = float(line.get("cost") or 0)
        amount_pos = float(line.get("amount") or 0) or max(0.0, qty_pos * cost)
        qty = -abs(qty_pos)
        amount = -abs(amount_pos)
        line_vat = -round(abs(amount_pos) * 0.07, 2) if is_vat else 0.0
        product = _fetch_icmas_row(conn, bcode) or {}
        conn.execute(
            pidet_insert,
            {
                "jourmode": jourmode,
                "billdate": billdate,
                "billtype": BILLTYPE,
                "billno": billno,
                "line": i * 10,
                "bcode": bcode,
                "pcode": product.get("PCODE") or None,
                "mcode": product.get("MCODE") or None,
                "detail": (line.get("descr") or "")[:60],
                "location1": str(product.get("LOCATION1") or "")[:10] or None,
                "isvat": "Y" if is_vat else "N",
                "qty": qty,
                "ui": (line.get("ui") or product.get("UI1") or "unit")[:10],
                "mtp": 1.0,
                "price": cost,
                "xprice": cost,
                "vat": line_vat,
                "amount": amount,
            },
        )
        new_qty = float(product.get("QTYOH2") or 0) + qty
        conn.execute(qtyoh2_update, {"qty": new_qty, "bcode": bcode})

    # Remark line (reason) — matches live KCCN style.
    conn.execute(
        pidet_insert,
        {
            "jourmode": jourmode,
            "billdate": billdate,
            "billtype": BILLTYPE,
            "billno": billno,
            "line": (len(lines) + 1) * 10,
            "bcode": None,
            "pcode": None,
            "mcode": None,
            "detail": "ลดหนี้จากรับสินค้า — ของขาด/ไม่ครบตามบิล"[:60],
            "location1": None,
            "isvat": "Y" if is_vat else "N",
            "qty": None,
            "ui": None,
            "mtp": 1.0,
            "price": None,
            "xprice": None,
            "vat": 0.0,
            "amount": 0.0,
        },
    )
    return billno


def stamp_vendor_cn_doc(
    conn,
    *,
    cn_billno: str,
    vendor_cn_no: str,
    vendor_cn_date: date | datetime | None,
) -> None:
    """Fill real vendor credit-note number/date onto a temp 7KCCN bill."""
    billno = str(cn_billno or "").strip()
    note = str(vendor_cn_no or "").strip()[:15]
    if not billno:
        raise HqReceiveError("missing_cn", "ไม่พบเลขใบลดหนี้")
    if not note:
        raise HqReceiveError("missing_vendor_cn", "กรอกเลขที่ใบลดหนี้จากเจ้าหนี้")
    notedate = None
    if vendor_cn_date:
        if isinstance(vendor_cn_date, datetime):
            notedate = vendor_cn_date
        elif isinstance(vendor_cn_date, date):
            notedate = datetime(vendor_cn_date.year, vendor_cn_date.month, vendor_cn_date.day)
        else:
            raw = str(vendor_cn_date)[:10]
            notedate = datetime.strptime(raw, "%Y-%m-%d")
    row = conn.execute(
        text(
            """
            SELECT LTRIM(RTRIM(BILLNO)) AS BILLNO, CANCELED
            FROM dbo.PIMAS WITH (UPDLOCK, HOLDLOCK)
            WHERE LTRIM(RTRIM(BILLNO)) = :b
            """
        ),
        {"b": billno},
    ).mappings().first()
    if not row:
        raise HqReceiveError("cn_not_found", f"ไม่พบใบลดหนี้ {billno} ใน PARTS9")
    if str(row.get("CANCELED") or "").strip().upper() == "Y":
        raise HqReceiveError("cn_canceled", f"ใบลดหนี้ {billno} ถูกยกเลิกแล้ว")
    conn.execute(
        text(
            """
            UPDATE dbo.PIMAS
            SET NOTENO = :noteno,
                NOTEDATE = :notedate
            WHERE LTRIM(RTRIM(BILLNO)) = :b
            """
        ),
        {"noteno": note, "notedate": notedate, "b": billno},
    )
