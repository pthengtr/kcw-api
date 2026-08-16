from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine
from src.parts9_explorer.search import probe_sites

BKK = ZoneInfo("Asia/Bangkok")

_PO_HEADER_COLS = (
    "LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) AS DOCNO, DOCDATE, "
    "LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(ACCTNO,'')))) AS ACCTNO, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME, "
    "BEFORETAX, TAX, AFTERTAX, "
    "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLED,'')))) AS BILLED, "
    "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) AS CANCELED, "
    "LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(BILLNO,'')))) AS BILLNO, BILLDATE, "
    "LTRIM(RTRIM(CONVERT(nvarchar(4000), COALESCE(REMARKS,'')))) AS REMARKS"
)

_DATE_EXPR = "CONVERT(varchar(10), DOCDATE, 23)"


def _site(site: str) -> str:
    key = (site or "hq").strip().lower()
    return "syp" if key == "syp" else "hq"


def _s(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())[:10]
        except Exception:
            return str(value)
    return str(value).strip()


def _row(mapping: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in dict(mapping).items():
        key = str(k)
        if hasattr(v, "isoformat"):
            out[key] = str(v.isoformat())[:19].replace("T", " ")
        elif v is None:
            out[key] = ""
        else:
            out[key] = str(v).strip() if isinstance(v, str) else v
    return out


def default_date_window(days: int = 30) -> tuple[str, str]:
    today = datetime_today()
    start = today - timedelta(days=days)
    return start.isoformat(), today.isoformat()


def datetime_today() -> date:
    from datetime import datetime

    return datetime.now(BKK).date()


def list_purchase_orders(
    *,
    site: str,
    status: str = "all",
    q: str | None = None,
    dfrom: str | None = None,
    dto: str | None = None,
    limit: int = 50,
    offset: int = 0,
    scan_limit: int | None = None,
) -> dict[str, Any]:
    site_key = _site(site)
    st = (status or "all").strip().lower()
    if st not in ("open", "billed", "all"):
        st = "all"
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))
    default_from, default_to = default_date_window(30)
    dfrom = (dfrom or "").strip() or default_from
    dto = (dto or "").strip() or default_to
    qn = (q or "").strip() or None
    scan = max(lim, min(int(scan_limit or lim), 2000))

    where = [f"{_DATE_EXPR} >= :dfrom", f"{_DATE_EXPR} <= :dto"]
    params: dict[str, Any] = {"dfrom": dfrom, "dto": dto, "lim": scan, "off": 0 if scan_limit else off}
    if st == "open":
        where.append("LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLED,'N')))) = 'N'")
        where.append("LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'")
    elif st == "billed":
        where.append("LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLED,'')))) = 'Y'")
    if qn:
        params["qlike"] = f"%{qn}%"
        where.append(
            "(LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) LIKE :qlike "
            "OR LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) LIKE :qlike "
            "OR LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(ACCTNO,'')))) LIKE :qlike)"
        )
    where_sql = " AND ".join(where)
    count_sql = text(f"SELECT COUNT(*) AS n FROM dbo.POMAS WHERE {where_sql}")
    list_sql = text(
        f"SELECT {_PO_HEADER_COLS} FROM dbo.POMAS WHERE {where_sql} "
        f"ORDER BY DOCDATE DESC, DOCNO DESC "
        f"OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY"
    )
    engine = get_site_engine(site_key)
    with engine.connect() as conn:
        total = int(conn.execute(count_sql, params).scalar() or 0)
        rows = [_header_row(r) for r in conn.execute(list_sql, params).mappings().all()]
    return {
        "site": site_key.upper(),
        "status": st,
        "from": dfrom,
        "to": dto,
        "q": qn or "",
        "count": total,
        "rows": rows,
        "live": True,
    }


def _header_row(mapping: Any) -> dict[str, Any]:
    r = _row(mapping)
    billed = _s(r.get("BILLED")).upper()
    canceled = _s(r.get("CANCELED")).upper()
    return {
        "docno": _s(r.get("DOCNO")),
        "docdate": _s(r.get("DOCDATE"))[:10],
        "acctno": _s(r.get("ACCTNO")),
        "acctname": _s(r.get("ACCTNAME")),
        "billed": billed,
        "canceled": canceled,
        "beforetax": r.get("BEFORETAX"),
        "tax": r.get("TAX"),
        "aftertax": r.get("AFTERTAX"),
        "billno": _s(r.get("BILLNO")),
        "billdate": _s(r.get("BILLDATE"))[:10],
        "remarks": _s(r.get("REMARKS")),
        "open": billed != "Y" and canceled != "Y",
    }


def get_po_lines(*, site: str, docno: str) -> dict[str, Any]:
    site_key = _site(site)
    doc = (docno or "").strip()
    if not doc:
        return {"docno": "", "header": None, "lines": [], "error": "missing docno"}
    engine = get_site_engine(site_key)
    header_sql = text(
        f"SELECT {_PO_HEADER_COLS} FROM dbo.POMAS WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) = :doc"
    )
    lines_sql = text(
        """
        SELECT
          LTRIM(RTRIM(CONVERT(nvarchar(80), d.DOCNO))) AS DOCNO,
          LTRIM(RTRIM(CONVERT(nvarchar(20), COALESCE(CONVERT(varchar(20), d.LINE), '')))) AS LINE,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(d.ITEMNO,'')))) AS ITEMNO,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(d.BCODE,'')))) AS BCODE,
          LTRIM(RTRIM(CONVERT(nvarchar(4000), COALESCE(d.DETAIL,'')))) AS DETAIL,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(d.MCODE,'')))) AS MCODE,
          d.QTY, d.UI, d.MTP, d.PRICE, d.AMOUNT,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(i.LOCATION1,'')))) AS LOCATION1,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(i.LOCATION2,'')))) AS LOCATION2,
          i.QTYOH2
        FROM dbo.PODET d
        LEFT JOIN dbo.ICMAS i ON LTRIM(RTRIM(CONVERT(nvarchar(40), i.BCODE))) = LTRIM(RTRIM(CONVERT(nvarchar(40), d.BCODE)))
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), d.DOCNO))) = :doc
        ORDER BY d.LINE
        """
    )
    with engine.connect() as conn:
        header_raw = conn.execute(header_sql, {"doc": doc}).mappings().first()
        line_rows = [_line_row(r) for r in conn.execute(lines_sql, {"doc": doc}).mappings().all()]
    header = _header_row(header_raw) if header_raw else None
    if site_key == "syp" and line_rows:
        _attach_hq_qty(line_rows)
    return {"docno": doc, "site": site_key.upper(), "header": header, "lines": line_rows, "live": True}


def _line_row(mapping: Any) -> dict[str, Any]:
    r = _row(mapping)
    return {
        "docno": _s(r.get("DOCNO")),
        "line": _s(r.get("LINE")),
        "itemno": _s(r.get("ITEMNO")),
        "bcode": _s(r.get("BCODE")),
        "detail": _s(r.get("DETAIL")),
        "mcode": _s(r.get("MCODE")),
        "qty": r.get("QTY"),
        "ui": _s(r.get("UI")),
        "mtp": r.get("MTP"),
        "price": r.get("PRICE"),
        "amount": r.get("AMOUNT"),
        "location1": _s(r.get("LOCATION1")),
        "location2": _s(r.get("LOCATION2")),
        "qtyoh2": r.get("QTYOH2"),
        "hq_qty": None,
        "hq_location1": None,
        "hq_location2": None,
    }


def _attach_hq_qty(lines: list[dict[str, Any]]) -> None:
    codes = sorted({ln["bcode"] for ln in lines if ln.get("bcode")})
    if not codes:
        return
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    sql = text(
        f"SELECT LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE, QTYOH2, "
        f"LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(LOCATION1,'')))) AS LOCATION1, "
        f"LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(LOCATION2,'')))) AS LOCATION2 "
        f"FROM dbo.ICMAS WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})"
    )
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            hq = {
                _s(r["BCODE"]): r
                for r in conn.execute(sql, params).mappings().all()
            }
    except Exception:
        return
    for ln in lines:
        row = hq.get(ln["bcode"])
        if not row:
            continue
        ln["hq_qty"] = row.get("QTYOH2")
        ln["hq_location1"] = _s(row.get("LOCATION1"))
        ln["hq_location2"] = _s(row.get("LOCATION2"))


def list_pending_receive(
    *,
    site: str,
    q: str | None = None,
    dfrom: str | None = None,
    dto: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Open ค้างรับ: ICLOW ORDERED=Y, RECEIVED=N, not canceled. Live PARTS9."""
    site_key = _site(site)
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))
    default_from, default_to = default_date_window(365)
    dfrom = (dfrom or "").strip() or default_from
    dto = (dto or "").strip() or default_to
    qn = (q or "").strip() or None
    pending = (
        "ORDERED = 'Y' AND ISNULL(RECEIVED,'N') = 'N' "
        "AND ISNULL(CANCELED,'N') <> 'Y'"
    )
    where = [pending, f"{_DATE_EXPR} >= :dfrom", f"{_DATE_EXPR} <= :dto"]
    params: dict[str, Any] = {"dfrom": dfrom, "dto": dto, "lim": lim, "off": off}
    if qn:
        params["qlike"] = f"%{qn}%"
        where.append(
            "(LTRIM(RTRIM(DOCNO)) LIKE :qlike "
            "OR LTRIM(RTRIM(COALESCE(VENDOR,''))) LIKE :qlike "
            "OR LTRIM(RTRIM(COALESCE(BCODE,''))) LIKE :qlike "
            "OR LTRIM(RTRIM(COALESCE(DESCR,''))) LIKE :qlike)"
        )
    where_sql = " AND ".join(where)
    count_sql = text(
        f"SELECT COUNT(*) AS n FROM ("
        f" SELECT LTRIM(RTRIM(DOCNO)) AS DOCNO FROM dbo.ICLOW WHERE {where_sql} "
        f" GROUP BY LTRIM(RTRIM(DOCNO))"
        f") x"
    )
    list_sql = text(
        f"""
        SELECT LTRIM(RTRIM(DOCNO)) AS DOCNO,
               MAX(CONVERT(varchar(10), DOCDATE, 23)) AS DOCDATE,
               MAX(LTRIM(RTRIM(COALESCE(VENDOR,'')))) AS VENDOR,
               COUNT(*) AS lines,
               SUM(CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), AMOUNT), ',', '')) = 1
                        THEN CONVERT(decimal(18,2), REPLACE(CONVERT(varchar(40), AMOUNT), ',', ''))
                        ELSE 0 END) AS amount
        FROM dbo.ICLOW
        WHERE {where_sql}
        GROUP BY LTRIM(RTRIM(DOCNO))
        ORDER BY MAX(DOCDATE) DESC, LTRIM(RTRIM(DOCNO)) DESC
        OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
        """
    )
    engine = get_site_engine(site_key)
    with engine.connect() as conn:
        total = int(conn.execute(count_sql, params).scalar() or 0)
        rows = []
        for r in conn.execute(list_sql, params).mappings().all():
            rr = _row(r)
            rows.append(
                {
                    "docno": _s(rr.get("DOCNO")),
                    "docdate": _s(rr.get("DOCDATE"))[:10],
                    "vendor": _s(rr.get("VENDOR")),
                    "lines": rr.get("lines") or rr.get("LINES") or 0,
                    "amount": rr.get("amount") or rr.get("AMOUNT"),
                    "status": "pending_receive",
                }
            )
    return {
        "site": site_key.upper(),
        "from": dfrom,
        "to": dto,
        "q": qn or "",
        "count": total,
        "rows": rows,
        "live": True,
    }


def health_probes() -> dict[str, Any]:
    return probe_sites()
