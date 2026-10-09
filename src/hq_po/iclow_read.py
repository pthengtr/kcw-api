"""Read HQ ICLOW rows. This module never updates RECEIVED."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine

_PAGE = 400

_NV = lambda col, n: f"LTRIM(RTRIM(CONVERT(nvarchar({n}), COALESCE({col},''))))"
_QTY = (
    "CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), QTY), ',', '')) = 1 "
    "THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), QTY), ',', '')) "
    "ELSE 0 END"
)
_NOT_CANCELED = f"{_NV('CANCELED', 10)} <> 'Y'"
_ORDERED_N = f"{_NV('ORDERED', 10)} <> 'Y'"


def _qty(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _row_from_mapping(row: Any) -> dict[str, Any]:
    return {
        "iclow_id": int(row["ID"]),
        "vendor": str(row.get("VENDOR") or "").strip(),
        "bcode": str(row.get("BCODE") or "").strip(),
        "descr": str(row.get("DESCR") or "").strip(),
        "mcode": str(row.get("MCODE") or "").strip(),
        "qty": _qty(row.get("QTY")),
        "ui": str(row.get("UI") or "").strip(),
        "ordered": str(row.get("ORDERED") or "").strip().upper(),
        "received": str(row.get("RECEIVED") or "").strip().upper(),
        "canceled": str(row.get("CANCELED") or "").strip().upper(),
        "docno": str(row.get("DOCNO") or "").strip(),
        "rcvdno": str(row.get("RCVDNO") or "").strip(),
        "rcvddate": str(row.get("RCVDDATE") or "").strip()[:10],
    }


_SELECT = f"""
    CONVERT(bigint, ID) AS ID,
    {_NV('VENDOR', 40)} AS VENDOR,
    {_NV('BCODE', 40)} AS BCODE,
    {_NV('DESCR', 400)} AS DESCR,
    {_NV('MCODE', 80)} AS MCODE,
    {_QTY} AS QTY,
    {_NV('UI', 20)} AS UI,
    {_NV('ORDERED', 10)} AS ORDERED,
    {_NV('RECEIVED', 10)} AS RECEIVED,
    {_NV('CANCELED', 10)} AS CANCELED,
    {_NV('DOCNO', 80)} AS DOCNO,
    {_NV('RCVDNO', 40)} AS RCVDNO,
    CONVERT(varchar(10), RCVDDATE, 23) AS RCVDDATE
"""


def fetch_to_order_rows() -> list[dict[str, Any]]:
    """Every HQ ICLOW line still waiting to be ordered."""
    engine = get_site_engine("hq")
    rows: list[dict[str, Any]] = []
    offset = 0
    sql = text(
        f"""
        SELECT {_SELECT}
        FROM dbo.ICLOW
        WHERE {_NOT_CANCELED} AND {_ORDERED_N}
        ORDER BY {_NV('VENDOR', 40)}, {_NV('BCODE', 40)}, ID
        OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
        """
    )
    with engine.connect() as conn:
        while True:
            batch = conn.execute(sql, {"off": offset, "lim": _PAGE}).mappings().all()
            if not batch:
                break
            rows.extend(_row_from_mapping(row) for row in batch)
            if len(batch) < _PAGE:
                break
            offset += _PAGE
    return rows


def fetch_iclow_by_ids(iclow_ids: list[int]) -> dict[int, dict[str, Any]]:
    ids = []
    seen: set[int] = set()
    for raw in iclow_ids:
        try:
            iclow_id = int(raw)
        except (TypeError, ValueError):
            continue
        if iclow_id > 0 and iclow_id not in seen:
            seen.add(iclow_id)
            ids.append(iclow_id)
    if not ids:
        return {}
    engine = get_site_engine("hq")
    out: dict[int, dict[str, Any]] = {}
    with engine.connect() as conn:
        for start in range(0, len(ids), 80):
            chunk = ids[start : start + 80]
            params = {f"i{n}": iclow_id for n, iclow_id in enumerate(chunk)}
            placeholders = ", ".join(f":i{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT {_SELECT}
                FROM dbo.ICLOW
                WHERE CONVERT(bigint, ID) IN ({placeholders})
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                parsed = _row_from_mapping(row)
                out[parsed["iclow_id"]] = parsed
    return out


def fetch_incoming_qty() -> dict[str, float]:
    """Qty already ordered and not received, by product. This is ค้างรับ."""
    engine = get_site_engine("hq")
    sql = text(
        f"""
        SELECT {_NV('BCODE', 40)} AS BCODE, SUM({_QTY}) AS QTY
        FROM dbo.ICLOW
        WHERE {_NV('ORDERED', 10)} = 'Y'
          AND {_NV('RECEIVED', 10)} <> 'Y'
          AND {_NOT_CANCELED}
        GROUP BY {_NV('BCODE', 40)}
        """
    )
    out: dict[str, float] = {}
    with engine.connect() as conn:
        for row in conn.execute(sql).mappings().all():
            bcode = str(row.get("BCODE") or "").strip()
            qty = _qty(row.get("QTY"))
            if bcode and qty > 0:
                out[bcode] = qty
    return out


def fetch_unordered_bcodes(bcodes: list[str]) -> set[str]:
    """Products that already have a waiting-to-order ICLOW row."""
    codes = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    if not codes:
        return set()
    engine = get_site_engine("hq")
    out: set[str] = set()
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"b{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":b{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT DISTINCT {_NV('BCODE', 40)} AS BCODE
                FROM dbo.ICLOW
                WHERE {_NV('BCODE', 40)} IN ({placeholders})
                  AND {_NOT_CANCELED}
                  AND {_ORDERED_N}
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                bcode = str(row.get("BCODE") or "").strip()
                if bcode:
                    out.add(bcode)
    return out


def fetch_vendor_names(acctnos: list[str]) -> dict[str, str]:
    codes = []
    seen: set[str] = set()
    for raw in acctnos:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    if not codes:
        return {}
    engine = get_site_engine("hq")
    out: dict[str, str] = {}
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"a{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":a{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT
                  LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME
                FROM dbo.APMAS
                WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) IN ({placeholders})
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                acct = str(row.get("ACCTNO") or "").strip()
                name = str(row.get("ACCTNAME") or "").strip()
                if acct and name:
                    out[acct] = name
    return out
