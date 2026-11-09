"""Write vendor purchase receive into HQ PARTS9 PIMAS/PIDET and stamp ICLOW.

Flag-gated via HQ_RECEIVE_PIMAS_WRITE_ENABLED. When off, returns a dry-run plan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.docno import bn_prefix, format_bn
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.rules import VARIANCE_WAIT_REST, assert_confirmable, line_received_qty, qty_tolerance
from src.hq_receive.writers.credit_note_pimas import insert_credit_note, plan_credit_note
from src.transfer.writers._engine import (
    _fetch_icmas_row,
    transfer_write_permission_hint,
    writer_engine_for_branch,
)

BOOKNO = "1"
JOURMODE = "2"
BILLTYPE = "1"  # purchase invoice style used by live BN bills


def _next_bn(conn, when: datetime) -> str:
    prefix = bn_prefix(when)
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
    return format_bn(seq + 1, when)


def _money(line: dict[str, Any]) -> tuple[float, float, float]:
    qty = float(line.get("qty") or 0)
    cost = float(line.get("cost") or 0)
    discount = float(line.get("discount") or 0)
    amount = float(line.get("amount") or 0)
    if amount <= 0:
        amount = max(0.0, qty * cost - discount)
    return qty, cost, amount


def _apply_iclow_receive(
    conn,
    *,
    iclow_id: int,
    line: dict[str, Any],
    rcvdno: str,
    rcvddate: datetime,
) -> str:
    """Stamp RECEIVED when the open qty is fully covered; otherwise reduce ICLOW.QTY.

    Wait-rest / partial physical receive leaves the remainder as ค้างรับ.
    Credit-note and full receive close the ICLOW row.
    """
    row = conn.execute(
        text(
            """
            SELECT
              CONVERT(bigint, ID) AS ID,
              CONVERT(float, COALESCE(QTY, 0)) AS QTY
            FROM dbo.ICLOW WITH (UPDLOCK, HOLDLOCK)
            WHERE CONVERT(bigint, ID) = :iclow_id
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) = 'Y'
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
            """
        ),
        {"iclow_id": int(iclow_id)},
    ).mappings().first()
    if not row:
        raise HqReceiveError(
            "iclow_missing",
            f"ไม่พบค้างรับ ICLOW {iclow_id} หรือรับไปแล้ว",
        )

    open_qty = float(row.get("QTY") or 0)
    received = line_received_qty(line)
    action = str(line.get("variance_action") or "").strip().lower()
    # Only wait_rest keeps a remainder on the same ICLOW row.
    keep_remainder = action == VARIANCE_WAIT_REST and received + qty_tolerance() < open_qty
    if keep_remainder:
        remaining = round(max(0.0, open_qty - received), 4)
        if remaining <= qty_tolerance():
            keep_remainder = False
        else:
            updated = conn.execute(
                text(
                    """
                    UPDATE dbo.ICLOW
                    SET QTY = :qty
                    WHERE CONVERT(bigint, ID) = :iclow_id
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) = 'Y'
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
                    """
                ),
                {"qty": remaining, "iclow_id": int(iclow_id)},
            )
            if updated.rowcount != 1:
                raise HqReceiveError(
                    "iclow_conflict",
                    f"ลดจำนวนค้างรับ ICLOW {iclow_id} ไม่สำเร็จ",
                )
            return "reduced"

    stamped = conn.execute(
        text(
            """
            UPDATE dbo.ICLOW
            SET RECEIVED = 'Y',
                RCVDNO = :rcvdno,
                RCVDDATE = :rcvddate
            WHERE CONVERT(bigint, ID) = :iclow_id
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) = 'Y'
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'
              AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
            """
        ),
        {
            "rcvdno": rcvdno[:40],
            "rcvddate": rcvddate,
            "iclow_id": int(iclow_id),
        },
    )
    if stamped.rowcount != 1:
        raise HqReceiveError(
            "iclow_conflict",
            f"ปิดค้างรับ ICLOW {iclow_id} ไม่สำเร็จ",
        )
    return "received"


def plan_receive(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate and describe what would be written. Never touches PARTS9."""
    lines = assert_confirmable(receipt)
    acctno = str(receipt.get("vendor_acctno") or "").strip()
    if not acctno:
        raise HqReceiveError("missing_vendor", "ยังไม่ได้เลือกเจ้าหนี้")

    subtotal = 0.0
    for ln in lines:
        _, _, amount = _money(ln)
        subtotal += amount
    discount = float(receipt.get("discount") or 0)
    before = max(0.0, subtotal - discount)
    vat_flag = int(receipt.get("vat") or 0)
    # UI stores VAT amount in vat when > 1, or 0/7 flag; prefer explicit tax fields.
    tax = float(receipt.get("tax") or 0)
    if tax <= 0 and vat_flag == 7:
        tax = round(before * 0.07, 2)
    net = float(receipt.get("net") or 0) or round(before + tax, 2)

    cn_plan = plan_credit_note(receipt, source_billno="(preview)")
    return {
        "dry_run": True,
        "vendor_acctno": acctno,
        "vendor_name": receipt.get("vendor_name") or "",
        "vendor_billno": receipt.get("vendor_billno") or "",
        "line_count": len(lines),
        "beforetax": before,
        "tax": tax,
        "aftertax": net,
        "lines": lines,
        "credit_note": cn_plan,
        "write_enabled": get_hq_receive_settings().write_enabled,
    }


def post_vendor_receive(
    receipt: dict[str, Any],
    *,
    operator: str,
) -> dict[str, Any]:
    """Insert PIMAS/PIDET, bump ICMAS.QTYOH2, stamp ICLOW RECEIVED/RCVDNO on HQ KSS."""
    plan = plan_receive(receipt)
    settings = get_hq_receive_settings()
    if not settings.write_enabled:
        return {
            **plan,
            "status": "dry_run",
            "kcw_billno": None,
            "pimas_billno": None,
            "cn_billno": (plan.get("credit_note") or {}).get("prefix"),
            "message": "HQ_RECEIVE_PIMAS_WRITE_ENABLED ยังปิด — ยังไม่เขียน PARTS9",
        }

    engine = writer_engine_for_branch("hq")
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if receipt.get("receive_date"):
        try:
            raw = str(receipt["receive_date"])[:10]
            billdate = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            pass
    billtime = f"{now.hour:02d}{now.minute:02d}"
    acctno = plan["vendor_acctno"]
    acctname = (plan.get("vendor_name") or "")[:60]
    vendor_billno = (plan.get("vendor_billno") or "")[:15]
    po_docnos = receipt.get("po_docnos") or []
    po_field = ""
    if isinstance(po_docnos, list) and po_docnos:
        po_field = str(po_docnos[0])[:15]
    elif receipt.get("lines"):
        po_field = str((receipt["lines"][0] or {}).get("po_docno") or "")[:15]

    pay_method = str(receipt.get("pay_method") or "credit").lower()
    cashed = "Y" if pay_method in {"cash", "ชำระสด", "สด"} else "N"
    remarks = (str(receipt.get("receive_date") or now.strftime("%d/%m/%y"))[:30])

    cn_billno = None
    cn_plan = None
    billno = None
    before = float(plan["beforetax"])
    tax = float(plan["tax"])
    after = float(plan["aftertax"])
    try:
        with engine.begin() as conn:
            # Resolve vendor name from APMAS when missing.
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

            for line in plan["lines"]:
                bcode = str(line.get("bcode") or "").strip()
                if not bcode or not _fetch_icmas_row(conn, bcode):
                    raise HqReceiveError("missing_icmas", f"ไม่พบรหัส {bcode} ใน ICMAS")

            billno = _next_bn(conn, now)
            vat_flag = 1 if tax > 0 else 0

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
                      :discount, 0, :beforetax, :vat, :tax, :aftertax, 0, 0,
                      'N', :cashed, 0, 0, :dueamt,
                      :acctno, :acctname, :po, :sale, :re, :noteno, :remarks,
                      'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": JOURMODE,
                    "bookno": BOOKNO,
                    "billdate": billdate,
                    "jourtime": billtime,
                    "billtime": billtime,
                    "billtype": BILLTYPE,
                    "billno": billno,
                    "lines": len(plan["lines"]),
                    "discount": float(receipt.get("discount") or 0),
                    "beforetax": before,
                    "vat": vat_flag,
                    "tax": tax,
                    "aftertax": after,
                    "cashed": cashed,
                    "dueamt": 0 if cashed == "Y" else after,
                    "acctno": acctno,
                    "acctname": acctname,
                    "po": po_field or None,
                    "sale": (operator or "")[:15],
                    "re": "ตัด30"[:10],
                    "noteno": vendor_billno or None,
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
            for i, line in enumerate(plan["lines"], start=1):
                bcode = str(line.get("bcode") or "").strip()
                qty, cost, amount = _money(line)
                product = _fetch_icmas_row(conn, bcode) or {}
                line_vat = round(amount * 0.07, 2) if tax > 0 else 0.0
                conn.execute(
                    pidet_insert,
                    {
                        "jourmode": JOURMODE,
                        "billdate": billdate,
                        "billtype": BILLTYPE,
                        "billno": billno,
                        "line": i * 10,
                        "bcode": bcode,
                        "pcode": product.get("PCODE") or None,
                        "mcode": product.get("MCODE") or None,
                        "detail": (line.get("descr") or "")[:60],
                        "location1": str(product.get("LOCATION1") or "")[:10] or None,
                        "isvat": "Y" if tax > 0 else "N",
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
                iclow_id = line.get("iclow_id")
                if iclow_id:
                    _apply_iclow_receive(
                        conn,
                        iclow_id=int(iclow_id),
                        line=line,
                        rcvdno=billno[:40],
                        rcvddate=billdate,
                    )

            cn_plan = plan_credit_note(receipt, source_billno=billno)
            cn_billno = None
            if cn_plan:
                cn_billno = insert_credit_note(
                    conn,
                    cn_plan,
                    operator=operator,
                    billdate=billdate,
                    billtime=billtime,
                )
                cn_plan = {**cn_plan, "cn_billno": cn_billno}
    except HqReceiveError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="PIMAS/PIDET/ICMAS/ICLOW")
        if hint:
            raise HqReceiveError("permission_denied", hint) from exc
        raise HqReceiveError("sql_error", str(exc)) from exc

    return {
        "status": "confirmed",
        "dry_run": False,
        "kcw_billno": billno,
        "pimas_billno": billno,
        "cn_billno": cn_billno,
        "credit_note": cn_plan,
        "vendor_acctno": acctno,
        "line_count": len(plan["lines"]),
        "beforetax": before,
        "tax": tax,
        "aftertax": after,
    }
