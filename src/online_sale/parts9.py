from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.online_sale.errors import OnlineSaleError
from src.parts9_explorer.db import format_sql_error, get_site_engine
from src.transfer.parts9 import lookup_transfer_product

_PO_DUP = text(
    """
    SELECT TOP 5
      LTRIM(RTRIM(BILLNO)) AS billno,
      BILLDATE AS bill_date,
      LTRIM(RTRIM(PO)) AS online_po
    FROM dbo.SIMAS WITH (NOLOCK)
    WHERE LTRIM(RTRIM(ACCTNO)) = :acct
      AND LTRIM(RTRIM(COALESCE(PO, ''))) = :po
      AND UPPER(LTRIM(RTRIM(BILLNO))) LIKE 'TAD%'
      AND COALESCE(CANCELED, 'N') <> 'Y'
    ORDER BY BILLDATE DESC, BILLNO DESC
    """
)

_SEARCH = text(
    """
    SELECT TOP 40
      LTRIM(RTRIM(BILLNO)) AS billno,
      BILLDATE AS bill_date,
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(PO)) AS online_po,
      LTRIM(RTRIM(SALE)) AS sale,
      BEFORETAX AS beforetax,
      TAX AS tax,
      AFTERTAX AS aftertax,
      CANCELED AS canceled
    FROM dbo.SIMAS WITH (NOLOCK)
    WHERE (
        UPPER(LTRIM(RTRIM(BILLNO))) LIKE 'TAD%'
        OR UPPER(LTRIM(RTRIM(BILLNO))) LIKE 'CNTAD%'
      )
      AND (
        :q = ''
        OR UPPER(LTRIM(RTRIM(BILLNO))) LIKE :q_like
        OR UPPER(LTRIM(RTRIM(COALESCE(PO, '')))) LIKE :q_like
        OR UPPER(LTRIM(RTRIM(COALESCE(PO, '')))) = :q
      )
      AND (:acct = '' OR LTRIM(RTRIM(ACCTNO)) = :acct)
      AND (:date_from IS NULL OR BILLDATE >= :date_from)
      AND (:date_to IS NULL OR BILLDATE < :date_to)
    ORDER BY BILLDATE DESC, BILLNO DESC
    """
)

_HEADER = text(
    """
    SELECT TOP 1
      LTRIM(RTRIM(BILLNO)) AS billno,
      BILLDATE AS bill_date,
      BILLTIME AS bill_time,
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(PO)) AS online_po,
      LTRIM(RTRIM(SALE)) AS sale,
      LTRIM(RTRIM(REMARKS)) AS remarks,
      BEFORETAX AS beforetax,
      TAX AS tax,
      AFTERTAX AS aftertax,
      CANCELED AS canceled
    FROM dbo.SIMAS WITH (NOLOCK)
    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
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
      MTP AS mtp,
      PRICE AS price,
      AMOUNT AS amount,
      LTRIM(RTRIM(LOCATION1)) AS location1
    FROM dbo.SIDET WITH (NOLOCK)
    WHERE UPPER(LTRIM(RTRIM(BILLNO))) = :exact
      AND COALESCE(CANCELED, 'N') <> 'Y'
    ORDER BY LINE
    """
)

_CN_FOR_TAD = text(
    """
    SELECT
      LTRIM(RTRIM(d.BILLNO)) AS billno,
      LTRIM(RTRIM(d.BCODE)) AS bcode,
      d.QTY AS qty
    FROM dbo.SIDET d WITH (NOLOCK)
    INNER JOIN dbo.SIMAS h WITH (NOLOCK)
      ON LTRIM(RTRIM(h.BILLNO)) = LTRIM(RTRIM(d.BILLNO))
    WHERE UPPER(LTRIM(RTRIM(h.BILLNO))) LIKE 'CNTAD%'
      AND LTRIM(RTRIM(h.PO)) = :tad
      AND COALESCE(h.CANCELED, 'N') <> 'Y'
      AND COALESCE(d.CANCELED, 'N') <> 'Y'
    """
)


def _run(statement, params: dict):
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            return conn.execute(statement, params).mappings().all()
    except Exception as exc:
        raise OnlineSaleError("kss", format_sql_error(exc, site="hq"), status=502) from exc


def _day(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text_value = str(value).strip()
    return text_value[:10] if text_value else None


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def lookup_product(code: str) -> dict[str, Any]:
    raw = (code or "").strip()
    if not raw:
        raise OnlineSaleError("product", "ใส่รหัสสินค้าหรือสแกนบาร์โค้ด")
    hit = lookup_transfer_product(bcode=raw)
    if not hit:
        raise OnlineSaleError("product", f"ไม่พบสินค้า {raw}")
    ui1 = (hit.get("ui1") or "หน่วย").strip() or "หน่วย"
    ui2 = (hit.get("ui2") or "").strip()
    try:
        mtp2 = float(hit.get("mtp2") or 1) or 1.0
    except (TypeError, ValueError):
        mtp2 = 1.0
    if mtp2 <= 1:
        mtp2 = 1.0
        ui2 = ""
    return {
        "bcode": hit["bcode"],
        "descr": hit.get("descr") or "",
        "ui": ui1,
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
        "qtyoh2": float(hit.get("hq_qtyoh2") or 0),
        "location": hit.get("location_hq") or hit.get("location") or "",
        "location1": hit.get("location1") or hit.get("location_hq") or "",
        "pcode": hit.get("pcode") or "",
        "mcode": hit.get("mcode") or "",
        "price1": 0,
    }


def find_duplicate_po(
    acctno: str, online_po: str, *, exclude_billno: str = ""
) -> list[dict[str, Any]]:
    rows = _run(_PO_DUP, {"acct": acctno.strip(), "po": online_po.strip()})
    skip = (exclude_billno or "").strip().upper()
    out = []
    for r in rows:
        billno = str(r.get("billno") or "").strip()
        if skip and billno.upper() == skip:
            continue
        out.append(
            {
                "billno": billno,
                "bill_date": _day(r.get("bill_date")),
                "online_po": str(r.get("online_po") or "").strip(),
            }
        )
    return out


def search_bills(
    *,
    q: str = "",
    acctno: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    platform: str = "",
) -> list[dict[str, Any]]:
    from src.online_sale.shops import detect_platform

    raw_q = (q or "").strip().upper()
    # Also match TO via to_bill overlay later in service.
    params = {
        "q": raw_q,
        "q_like": f"{raw_q}%" if raw_q else "%",
        "acct": (acctno or "").strip(),
        "date_from": date_from or None,
        "date_to": date_to or None,
    }
    # date_to exclusive: bump by parsing in SQL as < next day — caller passes next day or same day end.
    rows = _run(_SEARCH, params)
    out = []
    for r in rows:
        acctname = str(r.get("acctname") or "")
        plat = detect_platform(acctname, str(r.get("acctno") or ""))
        if platform and plat != platform.strip().lower():
            continue
        billno = str(r.get("billno") or "").strip().upper()
        kind = "cntad" if billno.startswith("CNTAD") else "tad"
        out.append(
            {
                "billno": billno,
                "kind": kind,
                "bill_date": _day(r.get("bill_date")),
                "acctno": str(r.get("acctno") or "").strip(),
                "acctname": acctname.strip(),
                "platform": plat,
                "online_po": str(r.get("online_po") or "").strip(),
                "sale": str(r.get("sale") or "").strip(),
                "beforetax": _num(r.get("beforetax")),
                "tax": _num(r.get("tax")),
                "aftertax": _num(r.get("aftertax")),
                "canceled": str(r.get("canceled") or "N").strip().upper() == "Y",
            }
        )
    return out


def load_bill(billno: str) -> dict[str, Any]:
    from src.online_sale.shops import detect_platform, shop_display_name

    exact = (billno or "").strip().upper()
    if not exact:
        raise OnlineSaleError("bill", "ระบุเลขบิล")
    rows = _run(_HEADER, {"exact": exact})
    if not rows:
        raise OnlineSaleError("bill", f"ไม่พบบิล {exact}", status=404)
    h = rows[0]
    lines = [
        {
            "line_no": int(r.get("line_no") or 0),
            "bcode": str(r.get("bcode") or "").strip(),
            "detail": str(r.get("detail") or "").strip(),
            "qty": _num(r.get("qty")),
            "ui": str(r.get("ui") or "").strip(),
            "mtp": _num(r.get("mtp")) or 1.0,
            "price": _num(r.get("price")),
            "amount": _num(r.get("amount")),
            "location1": str(r.get("location1") or "").strip(),
        }
        for r in _run(_LINES, {"exact": exact})
    ]
    acctno = str(h.get("acctno") or "").strip()
    acctname = str(h.get("acctname") or "").strip()
    plat = detect_platform(acctname, acctno)
    return {
        "billno": exact,
        "kind": (
            "cntad"
            if exact.startswith("CNTAD") or exact.startswith("3CNTAD")
            else "tad"
        ),
        "bill_date": _day(h.get("bill_date")),
        "bill_time": str(h.get("bill_time") or "").strip(),
        "acctno": acctno,
        "acctname": acctname,
        "shop_name": shop_display_name(acctname),
        "platform": plat,
        "online_po": str(h.get("online_po") or "").strip(),
        "sale": str(h.get("sale") or "").strip(),
        "remarks": str(h.get("remarks") or "").strip(),
        "beforetax": _num(h.get("beforetax")),
        "tax": _num(h.get("tax")),
        "aftertax": _num(h.get("aftertax")),
        "canceled": str(h.get("canceled") or "N").strip().upper() == "Y",
        "lines": lines,
    }


def returned_qty_by_bcode(tad_billno: str) -> dict[str, Decimal]:
    """Sum absolute returned qty per bcode from existing CNTAD against this TAD."""
    rows = _run(_CN_FOR_TAD, {"tad": tad_billno.strip().upper()})
    out: dict[str, Decimal] = {}
    for r in rows:
        bcode = str(r.get("bcode") or "").strip()
        qty = abs(Decimal(str(r.get("qty") or 0)))
        out[bcode] = out.get(bcode, Decimal("0")) + qty
    return out
