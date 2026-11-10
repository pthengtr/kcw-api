"""Purchase and sales line history for the HQ PO Insight panel."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text

from src.db.engine import get_engine
from src.hq_po.guards import HqPoError

_BANGKOK = ZoneInfo("Asia/Bangkok")
_ALLOWED_MONTHS = {0, 3, 6, 12, 24}
_ROW_LIMIT = 80


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _site(site: str | None) -> str:
    return "syp" if str(site or "").strip().lower() == "syp" else "hq"


def _months(raw: Any) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 12
    return n if n in _ALLOWED_MONTHS else 12


def _since(months: int) -> str | None:
    if months <= 0:
        return None
    day = datetime.now(_BANGKOK).date() - timedelta(days=months * 30)
    return day.isoformat()


def _branch_code(site: str) -> str:
    return "SYP" if site == "syp" else "HQ"


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key.lower()] = value.date().isoformat()
        elif isinstance(value, date):
            out[key.lower()] = value.isoformat()
        elif isinstance(value, Decimal):
            out[key.lower()] = float(value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key.lower()] = float(value)
        else:
            out[key.lower()] = str(value or "").strip()
    return out


def purchase_history(bcode: str, *, site: str = "hq", months: int = 12) -> dict[str, Any]:
    code = str(bcode or "").strip()
    if not code:
        raise HqPoError("missing", "ไม่มีรหัสสินค้า")
    site_l = _site(site)
    months_n = _months(months)
    if site_l == "syp":
        return _purchase_parts9(code, site="syp", months=months_n)
    return _purchase_warehouse(code, months=months_n)


def sales_history(bcode: str, *, site: str = "hq", months: int = 12) -> dict[str, Any]:
    code = str(bcode or "").strip()
    if not code:
        raise HqPoError("missing", "ไม่มีรหัสสินค้า")
    site_l = _site(site)
    months_n = _months(months)
    return _sales_warehouse(code, branch=_branch_code(site_l), months=months_n)


def bill_detail(
    *,
    kind: str,
    billno: str,
    site: str = "hq",
    bcode: str = "",
) -> dict[str, Any]:
    doc = str(billno or "").strip()
    if not doc:
        raise HqPoError("missing", "ไม่มีเลขบิล")
    kind_l = str(kind or "").strip().lower()
    site_l = _site(site)
    if kind_l in ("purchase", "pi", "buy"):
        if site_l == "syp":
            return _purchase_bill_parts9(doc, site="syp", bcode=bcode)
        return _purchase_bill_warehouse(doc, bcode=bcode)
    if kind_l in ("sales", "si", "sell"):
        return _sales_bill_warehouse(doc, branch=_branch_code(site_l), bcode=bcode)
    raise HqPoError("missing", "เลือกได้แค่ประวัติซื้อหรือประวัติขาย")


def _purchase_warehouse(bcode: str, *, months: int) -> dict[str, Any]:
    since = _since(months)
    sql = text(
        """
        with base as (
            select
                trim(coalesce(p."BILLDATE", '')) as billdate,
                trim(coalesce(p."BILLNO", '')) as billno,
                trim(coalesce(p."ACCTNO", '')) as acctno,
                trim(coalesce(a."ACCTNAME", '')) as acctname,
                cast(nullif(replace(coalesce(p."QTY", '0'), ',', ''), '') as numeric) as qty,
                cast(nullif(replace(coalesce(p."PRICE", '0'), ',', ''), '') as numeric) as price,
                cast(nullif(replace(coalesce(p."AMOUNT", '0'), ',', ''), '') as numeric) as amount
            from raw_kcw.raw_hq_pidet_purchase_lines p
            left join raw_kcw.raw_hq_apmas_payable a
              on trim(coalesce(a."ACCTNO", '')) = trim(coalesce(p."ACCTNO", ''))
            where trim(coalesce(p."BCODE", '')) = :bcode
              and coalesce(trim(p."CANCELED"), '') <> 'Y'
              and (
                    cast(:since as text) is null
                    or cast(:since as text) = ''
                    or trim(coalesce(p."BILLDATE", '')) >= cast(:since as text)
                  )
        )
        select *
        from base
        order by billdate desc, billno desc
        limit :lim
        """
    )
    with get_engine().connect() as conn:
        rows = [_clean_row(dict(r)) for r in conn.execute(
            sql, {"bcode": bcode, "since": since or "", "lim": _ROW_LIMIT}
        ).mappings()]
    return {
        "kind": "purchase",
        "site": "hq",
        "bcode": bcode,
        "months": months,
        "rows": rows,
        "total": len(rows),
    }


def _sales_warehouse(bcode: str, *, branch: str, months: int) -> dict[str, Any]:
    since = _since(months)
    sql = text(
        """
        with base as (
            select
                trim(coalesce(s."BILLDATE", '')) as billdate,
                trim(coalesce(s."BILLNO", '')) as billno,
                trim(coalesce(s."BRANCH", '')) as branch,
                trim(coalesce(s."ACCTNO", '')) as acctno,
                trim(coalesce(a."ACCTNAME", '')) as acctname,
                cast(nullif(replace(coalesce(s."QTY", '0'), ',', ''), '') as numeric) as qty,
                cast(nullif(replace(coalesce(s."PRICE", '0'), ',', ''), '') as numeric) as price,
                case
                    when coalesce(s."AMOUNT_NUM", '') <> ''
                        then cast(nullif(replace(coalesce(s."AMOUNT_NUM", '0'), ',', ''), '') as numeric)
                    else cast(nullif(replace(coalesce(s."AMOUNT", '0'), ',', ''), '') as numeric)
                end as amount,
                cast(nullif(replace(coalesce(s."LAST_PURCHASE_COST", ''), ',', ''), '') as numeric) as cost,
                trim(coalesce(s."COST_STATUS", '')) as cost_status,
                trim(coalesce(s."TAXIC", '')) as taxic
            from curated_kcw.fact_sales_all s
            left join raw_kcw.raw_hq_armas_receivable a
              on trim(coalesce(a."ACCTNO", '')) = trim(coalesce(s."ACCTNO", ''))
            where trim(coalesce(s."BCODE", '')) = :bcode
              and upper(trim(coalesce(s."BRANCH", ''))) = :branch
              and coalesce(s."CANCELED", '') <> 'Y'
              and coalesce(s."JOURMODE", '') <> '0'
              and coalesce(s."BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
              and upper(btrim(s."BILLNO")) !~ '^(3)?SA'
              and (
                    cast(:since as text) is null
                    or cast(:since as text) = ''
                    or trim(coalesce(s."BILLDATE", '')) >= cast(:since as text)
                  )
        )
        select
            billdate, billno, branch, acctno, acctname, qty, price, amount, cost, cost_status, taxic,
            case
                when cost is null or qty is null then null
                else amount - (cost * qty)
            end as profit
        from base
        order by billdate desc, billno desc
        limit :lim
        """
    )
    with get_engine().connect() as conn:
        rows = [_clean_row(dict(r)) for r in conn.execute(
            sql,
            {"bcode": bcode, "branch": branch, "since": since or "", "lim": _ROW_LIMIT},
        ).mappings()]
    return {
        "kind": "sales",
        "site": "syp" if branch == "SYP" else "hq",
        "bcode": bcode,
        "months": months,
        "rows": rows,
        "total": len(rows),
    }


def _purchase_bill_warehouse(billno: str, *, bcode: str = "") -> dict[str, Any]:
    sql = text(
        """
        select
            trim(coalesce(p."BILLDATE", '')) as billdate,
            trim(coalesce(p."BILLNO", '')) as billno,
            trim(coalesce(p."ACCTNO", '')) as acctno,
            trim(coalesce(a."ACCTNAME", '')) as acctname,
            trim(coalesce(p."BCODE", '')) as bcode,
            trim(coalesce(p."DETAIL", '')) as detail,
            cast(nullif(replace(coalesce(p."QTY", '0'), ',', ''), '') as numeric) as qty,
            cast(nullif(replace(coalesce(p."PRICE", '0'), ',', ''), '') as numeric) as price,
            cast(nullif(replace(coalesce(p."AMOUNT", '0'), ',', ''), '') as numeric) as amount,
            trim(coalesce(p."UI", '')) as ui
        from raw_kcw.raw_hq_pidet_purchase_lines p
        left join raw_kcw.raw_hq_apmas_payable a
          on trim(coalesce(a."ACCTNO", '')) = trim(coalesce(p."ACCTNO", ''))
        where trim(coalesce(p."BILLNO", '')) = :billno
          and coalesce(trim(p."CANCELED"), '') <> 'Y'
        order by p."LINE"
        limit 200
        """
    )
    with get_engine().connect() as conn:
        rows = [_clean_row(dict(r)) for r in conn.execute(sql, {"billno": billno}).mappings()]
    head = rows[0] if rows else {}
    return {
        "kind": "purchase",
        "site": "hq",
        "billno": billno,
        "focus_bcode": str(bcode or "").strip(),
        "billdate": head.get("billdate") or "",
        "acctno": head.get("acctno") or "",
        "acctname": head.get("acctname") or "",
        "lines": rows,
    }


def _sales_bill_warehouse(billno: str, *, branch: str, bcode: str = "") -> dict[str, Any]:
    sql = text(
        """
        select
            trim(coalesce(s."BILLDATE", '')) as billdate,
            trim(coalesce(s."BILLNO", '')) as billno,
            trim(coalesce(s."BRANCH", '')) as branch,
            trim(coalesce(s."ACCTNO", '')) as acctno,
            trim(coalesce(a."ACCTNAME", '')) as acctname,
            trim(coalesce(s."BCODE", '')) as bcode,
            trim(coalesce(s."DETAIL", '')) as detail,
            cast(nullif(replace(coalesce(s."QTY", '0'), ',', ''), '') as numeric) as qty,
            cast(nullif(replace(coalesce(s."PRICE", '0'), ',', ''), '') as numeric) as price,
            case
                when coalesce(s."AMOUNT_NUM", '') <> ''
                    then cast(nullif(replace(coalesce(s."AMOUNT_NUM", '0'), ',', ''), '') as numeric)
                else cast(nullif(replace(coalesce(s."AMOUNT", '0'), ',', ''), '') as numeric)
            end as amount,
            cast(nullif(replace(coalesce(s."LAST_PURCHASE_COST", ''), ',', ''), '') as numeric) as cost,
            trim(coalesce(s."UI", '')) as ui
        from curated_kcw.fact_sales_all s
        left join raw_kcw.raw_hq_armas_receivable a
          on trim(coalesce(a."ACCTNO", '')) = trim(coalesce(s."ACCTNO", ''))
        where trim(coalesce(s."BILLNO", '')) = :billno
          and upper(trim(coalesce(s."BRANCH", ''))) = :branch
          and coalesce(s."CANCELED", '') <> 'Y'
        order by s."BCODE"
        limit 200
        """
    )
    with get_engine().connect() as conn:
        rows = [_clean_row(dict(r)) for r in conn.execute(
            sql, {"billno": billno, "branch": branch}
        ).mappings()]
    for row in rows:
        qty = _num(row.get("qty"))
        cost = _num(row.get("cost"))
        amount = _num(row.get("amount"))
        if qty is not None and cost is not None and amount is not None:
            row["profit"] = amount - (cost * qty)
    head = rows[0] if rows else {}
    return {
        "kind": "sales",
        "site": "syp" if branch == "SYP" else "hq",
        "billno": billno,
        "focus_bcode": str(bcode or "").strip(),
        "billdate": head.get("billdate") or "",
        "acctno": head.get("acctno") or "",
        "acctname": head.get("acctname") or "",
        "lines": rows,
    }


def _purchase_parts9(bcode: str, *, site: str, months: int) -> dict[str, Any]:
    from src.parts9_explorer.db import get_site_engine

    since = _since(months)
    sql = text(
        """
        SELECT TOP 80
          LTRIM(RTRIM(CONVERT(nvarchar(40), d.BILLDATE))) AS billdate,
          LTRIM(RTRIM(CONVERT(nvarchar(40), d.BILLNO))) AS billno,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(h.ACCTNO, '')))) AS acctno,
          LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(h.ACCTNAME, '')))) AS acctname,
          CONVERT(float, d.QTY) AS qty,
          CONVERT(float, d.PRICE) AS price,
          CONVERT(float, d.AMOUNT) AS amount
        FROM dbo.PIDET d
        LEFT JOIN dbo.PIMAS h
          ON LTRIM(RTRIM(h.BILLNO)) = LTRIM(RTRIM(d.BILLNO))
        WHERE LTRIM(RTRIM(d.BCODE)) = :bcode
          AND (
                :since = ''
                OR LTRIM(RTRIM(CONVERT(nvarchar(40), d.BILLDATE))) >= :since
              )
        ORDER BY d.BILLDATE DESC, d.BILLNO DESC
        """
    )
    try:
        with get_site_engine(site).connect() as conn:
            rows = [_clean_row(dict(r)) for r in conn.execute(
                sql, {"bcode": bcode, "since": since or ""}
            ).mappings()]
    except Exception as exc:
        raise HqPoError("vendor_mismatch", "อ่านประวัติซื้อไม่ได้") from exc
    return {
        "kind": "purchase",
        "site": site,
        "bcode": bcode,
        "months": months,
        "rows": rows,
        "total": len(rows),
    }


def _purchase_bill_parts9(billno: str, *, site: str, bcode: str = "") -> dict[str, Any]:
    from src.parts9_explorer.db import get_site_engine

    sql = text(
        """
        SELECT TOP 200
          LTRIM(RTRIM(CONVERT(nvarchar(40), d.BILLDATE))) AS billdate,
          LTRIM(RTRIM(CONVERT(nvarchar(40), d.BILLNO))) AS billno,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(h.ACCTNO, '')))) AS acctno,
          LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(h.ACCTNAME, '')))) AS acctname,
          LTRIM(RTRIM(CONVERT(nvarchar(40), d.BCODE))) AS bcode,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(d.DETAIL, '')))) AS detail,
          CONVERT(float, d.QTY) AS qty,
          CONVERT(float, d.PRICE) AS price,
          CONVERT(float, d.AMOUNT) AS amount,
          LTRIM(RTRIM(CONVERT(nvarchar(20), COALESCE(d.UI, '')))) AS ui
        FROM dbo.PIDET d
        LEFT JOIN dbo.PIMAS h
          ON LTRIM(RTRIM(h.BILLNO)) = LTRIM(RTRIM(d.BILLNO))
        WHERE LTRIM(RTRIM(d.BILLNO)) = :billno
        ORDER BY d.LINE
        """
    )
    try:
        with get_site_engine(site).connect() as conn:
            rows = [_clean_row(dict(r)) for r in conn.execute(
                sql, {"billno": billno}
            ).mappings()]
    except Exception as exc:
        raise HqPoError("vendor_mismatch", "อ่านรายละเอียดบิลไม่ได้") from exc
    head = rows[0] if rows else {}
    return {
        "kind": "purchase",
        "site": site,
        "billno": billno,
        "focus_bcode": str(bcode or "").strip(),
        "billdate": head.get("billdate") or "",
        "acctno": head.get("acctno") or "",
        "acctname": head.get("acctname") or "",
        "lines": rows,
    }
