"""Live HQ PARTS9 reads for one TAD. No writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text

from src.parts9_explorer.db import format_sql_error, get_site_engine
from src.to_bill.errors import ToBillError

_SEARCH = text(
    """
    SELECT TOP 12
      LTRIM(RTRIM(BILLNO)) AS billno,
      BILLDATE AS bill_date,
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(PO)) AS online_po,
      BEFORETAX AS beforetax,
      TAX AS tax,
      AFTERTAX AS aftertax,
      DISCOUNT AS discount,
      DEDUCT AS deduct,
      CANCELED AS canceled
    FROM dbo.SIMAS
    WHERE UPPER(LTRIM(RTRIM(BILLNO))) LIKE 'TAD%'
      AND (
        UPPER(LTRIM(RTRIM(BILLNO))) = :exact
        OR UPPER(LTRIM(RTRIM(BILLNO))) LIKE :prefix
        OR UPPER(LTRIM(RTRIM(COALESCE(PO, '')))) = :exact
      )
    ORDER BY BILLDATE DESC, BILLNO DESC
    """
)

_HEADER = text(
    """
    SELECT TOP 1
      LTRIM(RTRIM(BILLNO)) AS billno,
      BILLDATE AS bill_date,
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(PO)) AS online_po,
      BEFORETAX AS beforetax,
      TAX AS tax,
      AFTERTAX AS aftertax,
      DISCOUNT AS discount,
      DEDUCT AS deduct,
      CANCELED AS canceled
    FROM dbo.SIMAS
    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
      AND UPPER(LTRIM(RTRIM(BILLNO))) LIKE 'TAD%'
    """
)

_LINES = text(
    """
    SELECT
      LINE AS line_no,
      LTRIM(RTRIM(BCODE)) AS bcode,
      LTRIM(RTRIM(DETAIL)) AS detail,
      QTY AS qty,
      LTRIM(RTRIM(UI)) AS ui,
      PRICE AS price,
      AMOUNT AS amount
    FROM dbo.SIDET
    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
      AND COALESCE(CANCELED, 'N') <> 'Y'
    ORDER BY LINE
    """
)

_ARMAS = text(
    """
    SELECT TOP 1
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(ADDR1)) AS addr1,
      LTRIM(RTRIM(ADDR2)) AS addr2,
      LTRIM(RTRIM(PHONE)) AS phone,
      LTRIM(RTRIM(MOBILE)) AS tax_id,
      LTRIM(RTRIM(EMAIL)) AS email
    FROM dbo.ARMAS
    WHERE LTRIM(RTRIM(ACCTNO)) = :acct
    ORDER BY CASE WHEN COALESCE(CANCELED, 'N') = 'Y' THEN 1 ELSE 0 END, ID
    """
)


@dataclass
class LiveLine:
    line_no: int
    bcode: str
    detail: str
    qty: Decimal
    ui: str
    price: Decimal
    amount: Decimal


@dataclass
class LiveBill:
    billno: str
    bill_date: date | None
    acctno: str
    acctname: str
    online_po: str
    beforetax: Decimal
    tax: Decimal
    aftertax: Decimal
    discount: Decimal
    canceled: bool
    lines: list[LiveLine] = field(default_factory=list)
    armas: dict | None = None


def like_prefix(value: str) -> str:
    escaped = (
        value.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
    )
    return escaped + "%"


def is_tad_query(value: str) -> bool:
    return (value or "").strip().upper().startswith("TAD")


def _money(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _qty(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _day(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value).strip()
    if not text_value:
        return None
    return date.fromisoformat(text_value[:10])


def _canceled(value) -> bool:
    return str(value or "").strip().upper() == "Y"


def _discount(row) -> Decimal:
    return _money(row.get("discount")) + _money(row.get("deduct"))


def _header(row) -> LiveBill:
    return LiveBill(
        billno=str(row.get("billno") or "").strip().upper(),
        bill_date=_day(row.get("bill_date")),
        acctno=str(row.get("acctno") or "").strip(),
        acctname=str(row.get("acctname") or "").strip(),
        online_po=str(row.get("online_po") or "").strip(),
        beforetax=_money(row.get("beforetax")),
        tax=_money(row.get("tax")),
        aftertax=_money(row.get("aftertax")),
        discount=_discount(row),
        canceled=_canceled(row.get("canceled")),
    )


def _run(statement, params: dict):
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            return conn.execute(statement, params).mappings().all()
    except Exception as exc:
        raise ToBillError("kss", format_sql_error(exc, site="hq"), status=502) from exc


def search_tad(q: str) -> list[LiveBill]:
    raw = (q or "").strip()
    if len(raw) < 3:
        return []
    exact = raw.upper()
    rows = _run(_SEARCH, {"exact": exact, "prefix": like_prefix(exact)})
    return [_header(row) for row in rows if str(row.get("billno") or "").upper().startswith("TAD")]


def load_tad(billno: str) -> LiveBill | None:
    exact = (billno or "").strip().upper()
    if not exact.startswith("TAD"):
        return None
    rows = _run(_HEADER, {"exact": exact})
    if not rows:
        return None
    bill = _header(rows[0])
    line_rows = _run(_LINES, {"exact": exact})
    bill.lines = [
        LiveLine(
            line_no=int(row.get("line_no") or 0),
            bcode=str(row.get("bcode") or "").strip(),
            detail=str(row.get("detail") or "").strip(),
            qty=_qty(row.get("qty")),
            ui=str(row.get("ui") or "").strip(),
            price=_money(row.get("price")),
            amount=_money(row.get("amount")),
        )
        for row in line_rows
    ]
    if bill.acctno:
        armas_rows = _run(_ARMAS, {"acct": bill.acctno})
        if armas_rows:
            armas = dict(armas_rows[0])
            bill.armas = {key: str(armas.get(key) or "").strip() for key in armas}
    return bill
