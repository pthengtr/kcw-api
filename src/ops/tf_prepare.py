"""SYP prepare status from live HQ TF/TFV bills (SIMas.REMARKS → SYP DOCNO).

Matches kcw-v2 fn_po_syp_tf_prepare_status / fn_po_syp_docno_pattern.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine

DOCNO_RE = re.compile(r"[0-9]*PO[0-9]{4}-[0-9]+", re.I)


def is_tf_transfer_bill(billno: str | None) -> bool:
    b = (billno or "").strip().upper()
    return b.startswith("TF")


def extract_po_docno(remarks: str | None) -> str | None:
    m = DOCNO_RE.search(remarks or "")
    return m.group(0).upper() if m else None


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    s = str(value).strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _mtp(value: Any) -> float:
    n = _num(value)
    return n if n else 1.0


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def rollup_prepare_status(*, line_count: int, prepared_line_count: int, any_tf_line_count: int) -> str:
    if line_count <= 0 or any_tf_line_count <= 0:
        return "not_prepared"
    if prepared_line_count >= line_count:
        return "prepared"
    return "partially_prepared"


def line_prepare_status(*, ordered_qty: float, tf_qty: float) -> str:
    if tf_qty <= 0:
        return "not_prepared"
    if ordered_qty > 0 and tf_qty >= ordered_qty:
        return "prepared"
    return "partially_prepared"


def _fetch_tf_bills(docnos: list[str]) -> list[dict[str, str]]:
    docs = [d.strip() for d in docnos if (d or "").strip()]
    if not docs:
        return []
    clauses = []
    params: dict[str, str] = {}
    for i, doc in enumerate(docs):
        key = f"d{i}"
        params[key] = f"%{doc}%"
        clauses.append(f"CONVERT(nvarchar(4000), REMARKS) LIKE :{key}")
    sql = text(
        "SELECT LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) AS BILLNO, "
        "CONVERT(nvarchar(4000), REMARKS) AS REMARKS "
        "FROM dbo.SIMAS "
        "WHERE LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y' "
        "AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(40), BILLNO)))) LIKE 'TF%' "
        f"AND ({' OR '.join(clauses)})"
    )
    engine = get_site_engine("hq")
    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()
    wanted = {d.upper() for d in docs}
    out = []
    for r in rows:
        billno = _s(r.get("BILLNO"))
        if not is_tf_transfer_bill(billno):
            continue
        po = extract_po_docno(r.get("REMARKS"))
        if not po or po not in wanted:
            continue
        out.append({"billno": billno, "docno": po})
    return out


def _fetch_tf_line_qty(billnos: list[str]) -> dict[tuple[str, str], float]:
    """(billno, bcode) -> qty * mtp."""
    bills = [b.strip() for b in billnos if b]
    if not bills:
        return {}
    placeholders = ", ".join(f":b{i}" for i in range(len(bills)))
    params = {f"b{i}": b for i, b in enumerate(bills)}
    sql = text(
        "SELECT LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) AS BILLNO, "
        "LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE, "
        "QTY, MTP "
        "FROM dbo.SIDET "
        "WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) IN (" + placeholders + ") "
        "AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y' "
        "AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))), '') IS NOT NULL"
    )
    engine = get_site_engine("hq")
    qty: dict[tuple[str, str], float] = {}
    with engine.connect() as conn:
        for r in conn.execute(sql, params).mappings().all():
            key = (_s(r.get("BILLNO")).upper(), _s(r.get("BCODE")))
            qty[key] = qty.get(key, 0.0) + _num(r.get("QTY")) * _mtp(r.get("MTP"))
    return qty


def prepare_status_for_docnos(docnos: list[str]) -> dict[str, dict[str, Any]]:
    """Header rollup keyed by SYP DOCNO (uppercased match, original key preserved)."""
    docs = [d.strip() for d in docnos if (d or "").strip()]
    if not docs:
        return {}
    by_upper = {d.upper(): d for d in docs}
    tf_bills = _fetch_tf_bills(docs)
    billnos = sorted({b["billno"] for b in tf_bills})
    line_qty = _fetch_tf_line_qty(billnos)
    tf_qty_by_po_bcode: dict[tuple[str, str], float] = {}
    bills_by_po: dict[str, set[str]] = {}
    bill_to_po = {b["billno"].upper(): b["docno"].upper() for b in tf_bills}
    for b in tf_bills:
        bills_by_po.setdefault(b["docno"].upper(), set()).add(b["billno"])
    for (billno, bcode), q in line_qty.items():
        po = bill_to_po.get(billno.upper())
        if not po or not bcode:
            continue
        key = (po, bcode)
        tf_qty_by_po_bcode[key] = tf_qty_by_po_bcode.get(key, 0.0) + q

    engine = get_site_engine("syp")
    po_lines: dict[str, list[tuple[str, float]]] = {d.upper(): [] for d in docs}
    placeholders = ", ".join(f":p{i}" for i in range(len(docs)))
    params = {f"p{i}": d for i, d in enumerate(docs)}
    sql = text(
        "SELECT LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) AS DOCNO, "
        "LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE, QTY, MTP "
        "FROM dbo.PODET "
        "WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) IN (" + placeholders + ") "
        "AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))), '') IS NOT NULL"
    )
    with engine.connect() as conn:
        for r in conn.execute(sql, params).mappings().all():
            doc = _s(r.get("DOCNO")).upper()
            bcode = _s(r.get("BCODE"))
            ordered = _num(r.get("QTY")) * _mtp(r.get("MTP"))
            po_lines.setdefault(doc, []).append((bcode, ordered))

    out: dict[str, dict[str, Any]] = {}
    for upper, original in by_upper.items():
        lines = po_lines.get(upper) or []
        # grain: DOCNO+BCODE like v2
        by_bcode: dict[str, float] = {}
        for bcode, ordered in lines:
            by_bcode[bcode] = by_bcode.get(bcode, 0.0) + ordered
        line_count = 0
        prepared_line_count = 0
        any_tf_line_count = 0
        line_status: dict[str, dict[str, Any]] = {}
        for bcode, ordered in by_bcode.items():
            tf_qty = tf_qty_by_po_bcode.get((upper, bcode), 0.0)
            st = line_prepare_status(ordered_qty=ordered, tf_qty=tf_qty)
            line_status[bcode] = {
                "ordered_qty": ordered,
                "prepared_qty": tf_qty,
                "prepare_line_status": st,
            }
            if ordered <= 0:
                continue
            line_count += 1
            if tf_qty > 0:
                any_tf_line_count += 1
            if tf_qty >= ordered:
                prepared_line_count += 1
        status = rollup_prepare_status(
            line_count=line_count,
            prepared_line_count=prepared_line_count,
            any_tf_line_count=any_tf_line_count,
        )
        tf_billnos = ", ".join(sorted(bills_by_po.get(upper) or []))
        out[original] = {
            "docno": original,
            "prepare_status": status,
            "prepared": status == "prepared",
            "tf_billnos": tf_billnos or None,
            "prepared_line_count": prepared_line_count,
            "line_count": line_count,
            "lines": line_status,
        }
    return out


def attach_header_prepare(rows: list[dict[str, Any]]) -> None:
    docs = [r.get("docno") for r in rows if r.get("docno")]
    status = prepare_status_for_docnos(docs)
    for row in rows:
        info = status.get(row.get("docno") or "") or {}
        row["prepare_status"] = info.get("prepare_status") or "not_prepared"
        row["prepared"] = bool(info.get("prepared"))
        row["tf_billnos"] = info.get("tf_billnos")
        row["prepared_line_count"] = info.get("prepared_line_count")
        row["prepare_line_count"] = info.get("line_count")


def attach_bcode_prepare(rows: list[dict[str, Any]]) -> None:
    """ICLOW DOCNO+BCODE grain: use TF qty for that BCODE, not PO header rollup."""
    docs = sorted({r.get("docno") for r in rows if r.get("docno")})
    status = prepare_status_for_docnos(docs)
    for row in rows:
        info = status.get(row.get("docno") or "") or {}
        extra = (info.get("lines") or {}).get(_s(row.get("bcode"))) or {}
        st = extra.get("prepare_line_status") or "not_prepared"
        row["prepare_status"] = st
        row["prepared"] = st == "prepared"
        row["prepared_qty"] = extra.get("prepared_qty")
        row["prepare_tf_billnos"] = info.get("tf_billnos")


def attach_line_prepare(docno: str, lines: list[dict[str, Any]]) -> dict[str, Any]:
    info = prepare_status_for_docnos([docno]).get(docno) or {
        "prepare_status": "not_prepared",
        "prepared": False,
        "tf_billnos": None,
        "prepared_line_count": 0,
        "line_count": 0,
        "lines": {},
    }
    by_bcode = info.get("lines") or {}
    for ln in lines:
        extra = by_bcode.get(_s(ln.get("bcode"))) or {}
        ln["prepare_line_status"] = extra.get("prepare_line_status") or "not_prepared"
        ln["prepared"] = ln["prepare_line_status"] == "prepared"
        ln["prepared_qty"] = extra.get("prepared_qty")
        ln["ordered_qty"] = extra.get("ordered_qty")
    return info
