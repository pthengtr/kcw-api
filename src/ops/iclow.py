"""Live ICLOW stages matching kcw-v2 PoBranchTabs.

Tabs: รอสั่งซื้อ (to_be_ordered) · ค้างรับ (pending_receive) · รับบางส่วน (partially_received).
Grain: line for รอสั่งซื้อ, DOCNO+BCODE for the other two.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.ops.pi import resolve_pimas_batch
from src.ops.po import _row, _s, _site, default_date_window
from src.ops.tf_prepare import attach_bcode_prepare
from src.parts9_explorer.db import get_site_engine

ICLOW_STATUSES = ("to_be_ordered", "pending_receive", "partially_received")

_NV = (
    lambda col, n: f"LTRIM(RTRIM(CONVERT(nvarchar({n}), COALESCE({col},''))))"
)
_QTY = (
    "CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), QTY), ',', '')) = 1 "
    "THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), QTY), ',', '')) "
    "ELSE 0 END"
)
_DATE = "CONVERT(varchar(10), DOCDATE, 23)"
_NOT_CANCELED = f"{_NV('CANCELED', 10)} <> 'Y'"
_ORDERED_Y = f"{_NV('ORDERED', 10)} = 'Y'"
_ORDERED_N = f"{_NV('ORDERED', 10)} <> 'Y'"
_RECEIVED_Y = f"{_NV('RECEIVED', 10)} = 'Y'"


def list_iclow(
    *,
    site: str,
    status: str,
    q: str | None = None,
    dfrom: str | None = None,
    dto: str | None = None,
    prepare: str = "all",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    site_key = _site(site)
    st = (status or "pending_receive").strip().lower()
    if st not in ICLOW_STATUSES:
        st = "pending_receive"
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))
    qn = (q or "").strip() or None
    prep = (prepare or "all").strip().lower()
    if prep not in ("all", "prepared", "partially_prepared", "not_prepared"):
        prep = "all"

    scan = 800 if site_key == "syp" and (prep != "all" or st == "partially_received") else lim
    scan_off = 0 if scan > lim else off
    if st == "to_be_ordered":
        data = _list_to_be_ordered(site_key, qn, scan, scan_off)
    else:
        default_from, default_to = default_date_window(30)
        dfrom = (dfrom or "").strip() or default_from
        dto = (dto or "").strip() or default_to
        data = _list_bcode_stage(site_key, st, qn, dfrom, dto, scan, scan_off)

    rows = data["rows"]
    if site_key == "syp" and rows:
        attach_bcode_prepare(rows)
        if st == "partially_received":
            kept = []
            for r in rows:
                ordered = float(r.get("ordered_qty") or r.get("qty") or 0)
                tf_qty = float(r.get("prepared_qty") or 0)
                r["received_qty"] = tf_qty
                r["missing_qty"] = max(ordered - tf_qty, 0)
                if ordered > 0 and tf_qty < ordered:
                    kept.append(r)
            rows = kept
        if prep != "all":
            rows = [r for r in rows if (r.get("prepare_status") or "not_prepared") == prep]
        if scan > lim or st == "partially_received" or prep != "all":
            data["count"] = len(rows)
            data["rows"] = rows[off : off + lim]
        else:
            data["rows"] = rows
    elif site_key == "hq" and rows and st in ("pending_receive", "partially_received"):
        _attach_hq_pimas(rows)
    data["prepare"] = prep
    data["live"] = True
    return data


def _attach_hq_pimas(rows: list[dict[str, Any]]) -> None:
    rcvdnos = [str(r.get("rcvdno") or "").strip() for r in rows if r.get("rcvdno")]
    if not rcvdnos:
        for r in rows:
            r.setdefault("pimas_matched_billno", None)
            r.setdefault("pimas_match_method", None)
            r.setdefault("pimas_link_missing", False)
        return
    try:
        resolved = resolve_pimas_batch(rcvdnos)
    except Exception:
        for r in rows:
            r["pimas_matched_billno"] = None
            r["pimas_match_method"] = None
            r["pimas_link_missing"] = bool(str(r.get("rcvdno") or "").strip())
        return
    for r in rows:
        key = str(r.get("rcvdno") or "").strip()
        if not key:
            r["pimas_matched_billno"] = None
            r["pimas_match_method"] = None
            r["pimas_link_missing"] = False
            continue
        info = resolved.get(key) or {
            "pimas_matched_billno": None,
            "pimas_match_method": None,
            "pimas_link_missing": True,
        }
        r["pimas_matched_billno"] = info.get("pimas_matched_billno")
        r["pimas_match_method"] = info.get("pimas_match_method")
        r["pimas_link_missing"] = bool(info.get("pimas_link_missing"))


def _q_clause(qn: str | None, params: dict[str, Any], extra: tuple[str, ...] = ()) -> str:
    if not qn:
        return "1=1"
    params["qlike"] = f"%{qn}%"
    cols = (
        f"{_NV('DOCNO', 80)} LIKE :qlike",
        f"{_NV('VENDOR', 40)} LIKE :qlike",
        f"{_NV('BCODE', 40)} LIKE :qlike",
        f"{_NV('DESCR', 400)} LIKE :qlike",
        f"{_NV('MCODE', 80)} LIKE :qlike",
        *extra,
    )
    return "(" + " OR ".join(cols) + ")"


def _list_to_be_ordered(site_key: str, qn: str | None, lim: int, off: int) -> dict[str, Any]:
    params: dict[str, Any] = {"lim": lim, "off": off}
    where = [_NOT_CANCELED, _ORDERED_N, _q_clause(qn, params)]
    where_sql = " AND ".join(where)
    count_sql = text(f"SELECT COUNT(*) AS n FROM dbo.ICLOW WHERE {where_sql}")
    list_sql = text(
        f"""
        SELECT
          {_NV('DOCNO', 80)} AS DOCNO,
          {_DATE} AS DOCDATE,
          {_NV('VENDOR', 40)} AS VENDOR,
          {_NV('BCODE', 40)} AS BCODE,
          {_NV('DESCR', 400)} AS DESCR,
          {_NV('MCODE', 80)} AS MCODE,
          {_QTY} AS QTY,
          {_NV('UI', 20)} AS UI
        FROM dbo.ICLOW
        WHERE {where_sql}
        ORDER BY DOCDATE DESC, {_NV('VENDOR', 40)}, {_NV('BCODE', 40)}
        OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
        """
    )
    engine = get_site_engine(site_key)
    with engine.connect() as conn:
        total = int(conn.execute(count_sql, params).scalar() or 0)
        raw = conn.execute(list_sql, params).mappings().all()
    rows = []
    for r in raw:
        rr = _row(r)
        qty = rr.get("QTY") or 0
        rows.append(
            {
                "docno": _s(rr.get("DOCNO")),
                "docdate": _s(rr.get("DOCDATE"))[:10],
                "vendor": _s(rr.get("VENDOR")),
                "bcode": _s(rr.get("BCODE")),
                "descr": _s(rr.get("DESCR")),
                "mcode": _s(rr.get("MCODE")),
                "qty": qty,
                "ordered_qty": qty,
                "received_qty": 0,
                "missing_qty": qty,
                "ui": _s(rr.get("UI")),
                "status": "to_be_ordered",
                "grain": "line",
            }
        )
    return {
        "site": site_key.upper(),
        "status": "to_be_ordered",
        "from": "",
        "to": "",
        "q": qn or "",
        "count": total,
        "grain": "line",
        "rows": rows,
    }


def _list_bcode_stage(
    site_key: str,
    status: str,
    qn: str | None,
    dfrom: str,
    dto: str,
    lim: int,
    off: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"dfrom": dfrom, "dto": dto, "lim": lim, "off": off}
    inner_q = _q_clause(qn, params, extra=(f"{_NV('RCVDNO', 80)} LIKE :qlike",))
    having = (
        "MAX(CASE WHEN " + _RECEIVED_Y + " THEN 1 ELSE 0 END) = 0"
        if status == "pending_receive"
        else "MAX(CASE WHEN " + _RECEIVED_Y + " THEN 1 ELSE 0 END) = 1"
    )
    if status == "partially_received" and site_key != "syp":
        having = (
            "MAX(CASE WHEN " + _RECEIVED_Y + " THEN 1 ELSE 0 END) = 1 "
            "AND SUM(CASE WHEN " + _RECEIVED_Y + f" THEN {_QTY} ELSE 0 END) "
            f"< SUM({_QTY})"
        )
    grouped = f"""
        SELECT
          {_NV('DOCNO', 80)} AS DOCNO,
          MAX({_DATE}) AS DOCDATE,
          MAX({_NV('VENDOR', 40)}) AS VENDOR,
          {_NV('BCODE', 40)} AS BCODE,
          MAX({_NV('DESCR', 400)}) AS DESCR,
          MAX({_NV('MCODE', 80)}) AS MCODE,
          MAX({_NV('UI', 20)}) AS UI,
          SUM({_QTY}) AS ORDERED_QTY,
          SUM(CASE WHEN {_RECEIVED_Y} THEN {_QTY} ELSE 0 END) AS RECEIVED_QTY,
          MAX(CASE WHEN {_RECEIVED_Y} THEN {_NV('RCVDNO', 80)} ELSE '' END) AS RCVDNO,
          MAX(CASE WHEN {_RECEIVED_Y} THEN CONVERT(varchar(10), RCVDDATE, 23) ELSE '' END) AS RCVDDATE
        FROM dbo.ICLOW
        WHERE {_NOT_CANCELED}
          AND {_ORDERED_Y}
          AND {_NV('DOCNO', 80)} <> ''
          AND {_NV('BCODE', 40)} <> ''
          AND {_DATE} >= :dfrom AND {_DATE} <= :dto
          AND {inner_q}
        GROUP BY {_NV('DOCNO', 80)}, {_NV('BCODE', 40)}
        HAVING {having}
    """
    count_sql = text(f"SELECT COUNT(*) AS n FROM ({grouped}) x")
    list_sql = text(
        f"""
        SELECT * FROM ({grouped}) x
        ORDER BY DOCDATE DESC, DOCNO, BCODE
        OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
        """
    )
    engine = get_site_engine(site_key)
    with engine.connect() as conn:
        total = int(conn.execute(count_sql, params).scalar() or 0)
        raw = conn.execute(list_sql, params).mappings().all()
    rows = []
    for r in raw:
        rr = _row(r)
        ordered = rr.get("ORDERED_QTY") or 0
        received = rr.get("RECEIVED_QTY") or 0
        try:
            missing = max(float(ordered) - float(received), 0)
        except (TypeError, ValueError):
            missing = ordered
        rows.append(
            {
                "docno": _s(rr.get("DOCNO")),
                "docdate": _s(rr.get("DOCDATE"))[:10],
                "vendor": _s(rr.get("VENDOR")),
                "bcode": _s(rr.get("BCODE")),
                "descr": _s(rr.get("DESCR")),
                "mcode": _s(rr.get("MCODE")),
                "qty": ordered,
                "ordered_qty": ordered,
                "received_qty": received,
                "missing_qty": missing,
                "ui": _s(rr.get("UI")),
                "rcvdno": _s(rr.get("RCVDNO")),
                "rcvddate": _s(rr.get("RCVDDATE"))[:10],
                "status": status,
                "grain": "bcode",
            }
        )
    return {
        "site": site_key.upper(),
        "status": status,
        "from": dfrom,
        "to": dto,
        "q": qn or "",
        "count": total,
        "grain": "bcode",
        "rows": rows,
    }
