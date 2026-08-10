from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.stock_check.config import StockCheckSettings
from src.stock_check.parts9 import ProductRow, get_parts9_engine


class Parts9WriteError(RuntimeError):
    def __init__(self, message: str, *, code: str = "write_failed"):
        super().__init__(message)
        self.code = code


@dataclass
class PostedAdjustment:
    billno: str
    billtype: str
    qty_signed: float
    new_qtyoh2: float


def _next_billno(conn, prefix: str, when: datetime) -> str:
    """SA2608-00001 / 3SA2608-00001 — max 15 chars."""
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
        raise Parts9WriteError("generated BILLNO exceeds 15 chars", code="billno_overflow")
    return candidate


def _sa_remarks(operator_name: str, approver_name: str | None = None) -> str:
    """SIMAS.REMARKS is typically short (~30); encode counter + approver."""
    op = (operator_name or "STOCK").strip() or "STOCK"
    ap = (approver_name or "").strip()
    raw = f"SC:{op}/{ap}" if ap else f"SC:{op}"
    return raw[:30]


def post_stock_adjustment(
    *,
    settings: StockCheckSettings,
    product: ProductRow,
    variance: float,
    operator_name: str,
    approver_name: str | None = None,
    engine: Engine | None = None,
) -> PostedAdjustment:
    """
    Insert SIMAS+SIDET and update ICMAS.QTYOH2 in one transaction.

    variance = counted - system:
      < 0 → BILLTYPE 1, +abs qty (stock out)
      > 0 → BILLTYPE 2, -abs qty (stock in)

    SALE = operator; REMARKS = SC:{operator}/{approver} (truncated to 30).
    """
    if abs(variance) < 1e-9:
        raise Parts9WriteError("variance is zero; no bill", code="zero_variance")

    use_writer = bool(settings.pos_mssql_writer_username)
    eng = engine or get_parts9_engine(writer=use_writer)
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:2d}{now.minute:02d}"  # match POS spacing style loosely
    jourtime = f"{now.hour:02d}:{now.minute:02d}"
    abs_qty = abs(float(variance))
    if variance < 0:
        billtype = "1"
        qty_signed = abs_qty
    else:
        billtype = "2"
        qty_signed = -abs_qty

    jourmode = "2"  # non-VAT path like many zero-amount docs
    remarks = _sa_remarks(operator_name, approver_name)
    new_qty = float(product.qtyoh2) + float(variance)

    try:
        with eng.begin() as conn:
            # Permission probe / identity
            billno = _next_billno(conn, settings.bill_prefix, now)
            # Re-read live qty inside tx
            live = conn.execute(
                text(
                    """
                    SELECT QTYOH2 FROM dbo.ICMAS
                    WHERE LTRIM(RTRIM(BCODE)) = :bcode
                    """
                ),
                {"bcode": product.bcode},
            ).mappings().first()
            if not live:
                raise Parts9WriteError("product missing in ICMAS", code="missing_product")
            live_qty = float(live["QTYOH2"] or 0) if live["QTYOH2"] is not None else 0.0
            # Prefer applying variance against live system qty snapshot at approve
            new_qty = live_qty + float(variance)

            conn.execute(
                text(
                    """
                    INSERT INTO dbo.SIMAS (
                      JOURMODE, JOURTYPE, JOURDATE, JOURTIME, DEPTNO, BOOKNO,
                      BILLTYPE, BILLDATE, BILLTIME, BILLNO, LINES, TAXIC,
                      DISCOUNT, DEDUCT, BEFORETAX, VAT, TAX, AFTERTAX, EXEMPT, SVCCHG,
                      PAID, CASHED, CASHAMT, CHKAMT, DUEAMT,
                      SALE, REMARKS, POSTED1, POSTED2, CANCELED, DONE
                    ) VALUES (
                      :jourmode, 'SJ', :billdate, :jourtime, '1', '1',
                      :billtype, :billdate, :billtime, :billno, 1, 'N',
                      0, 0, 0, 0, 0, 0, 0, 0,
                      'Y', 'Y', 0, 0, 0,
                      :sale, :remarks, 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "billdate": billdate,
                    "jourtime": jourtime,
                    "billtype": billtype,
                    "billtime": billtime,
                    "billno": billno,
                    "sale": (operator_name or "STOCK")[:15],
                    "remarks": remarks,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.SIDET (
                      JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
                      LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
                      STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
                      QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
                      PAID, DONE, CANCELED
                    ) VALUES (
                      :jourmode, 'SJ', :billdate, :billtype, :billdate, :billno,
                      10, 1, :bcode, :pcode, :mcode, :detail, 'Y', :location1,
                      1, 'N', 'N', 'N', 'N',
                      :qty, :ui, :mtp, 0, 0, 0, 0,
                      'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "billdate": billdate,
                    "billtype": billtype,
                    "billno": billno,
                    "bcode": product.bcode,
                    "pcode": product.pcode or None,
                    "mcode": product.mcode or None,
                    "detail": (product.descr or "")[:60],
                    "location1": (product.location1 or "")[:10] or None,
                    "qty": qty_signed,
                    "ui": (product.ui1 or "หน่วย")[:10],
                    "mtp": product.mtp2 or 1.0,
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE dbo.ICMAS
                    SET QTYOH2 = :qty
                    WHERE LTRIM(RTRIM(BCODE)) = :bcode
                    """
                ),
                {"qty": new_qty, "bcode": product.bcode},
            )
    except Parts9WriteError:
        raise
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "permission" in msg.lower() or "denied" in msg.lower() or "424" in msg:
            raise Parts9WriteError(
                "PARTS9 write denied — grant writer login (INSERT SIMAS/SIDET, UPDATE ICMAS)",
                code="permission_denied",
            ) from exc
        raise Parts9WriteError(f"PARTS9 write failed: {msg}", code="write_failed") from exc

    return PostedAdjustment(
        billno=billno,
        billtype=billtype,
        qty_signed=qty_signed,
        new_qtyoh2=new_qty,
    )


def describe_write_access(settings: StockCheckSettings) -> dict[str, Any]:
    use_writer = bool(settings.pos_mssql_writer_username)
    eng = get_parts9_engine(writer=use_writer)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  HAS_PERMS_BY_NAME('dbo.SIMAS', 'OBJECT', 'INSERT') AS simas_insert,
                  HAS_PERMS_BY_NAME('dbo.SIDET', 'OBJECT', 'INSERT') AS sidet_insert,
                  HAS_PERMS_BY_NAME('dbo.ICMAS', 'OBJECT', 'UPDATE') AS icmas_update,
                  USER_NAME() AS dbuser
                """
            )
        ).mappings().first()
    return dict(row or {})
