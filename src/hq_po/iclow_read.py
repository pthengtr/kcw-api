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
        FROM dbo.ICLOW WITH (NOLOCK)
        WHERE {_NOT_CANCELED} AND {_ORDERED_N}
          AND {_NV('BCODE', 40)} LIKE '%[0-9]%'
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
                FROM dbo.ICLOW WITH (NOLOCK)
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
        FROM dbo.ICLOW WITH (NOLOCK)
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


def thumb_url(bcode: str) -> str:
    """First public product photo. An empty string means the line has no picture."""
    code = str(bcode or "").strip()
    if not code:
        return ""
    try:
        from src.parts9_explorer.search import product_image_urls

        urls = product_image_urls(code)
    except Exception:
        return ""
    return urls[0] if urls else ""


def fetch_incoming_lines() -> list[dict[str, Any]]:
    """HQ ICLOW lines already ordered and not received. This is the ค้างรับ list."""
    engine = get_site_engine("hq")
    rows: list[dict[str, Any]] = []
    offset = 0
    sql = text(
        f"""
        SELECT {_SELECT},
          CONVERT(varchar(10), DOCDATE, 23) AS DOCDATE
        FROM dbo.ICLOW WITH (NOLOCK)
        WHERE {_NV('ORDERED', 10)} = 'Y'
          AND {_NV('RECEIVED', 10)} <> 'Y'
          AND {_NOT_CANCELED}
          AND {_NV('BCODE', 40)} LIKE '%[0-9]%'
        ORDER BY {_NV('VENDOR', 40)}, {_NV('BCODE', 40)}, ID
        OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
        """
    )
    with engine.connect() as conn:
        while True:
            batch = conn.execute(sql, {"off": offset, "lim": _PAGE}).mappings().all()
            if not batch:
                break
            for row in batch:
                parsed = _row_from_mapping(row)
                parsed["docdate"] = str(row.get("DOCDATE") or "")[:10]
                rows.append(parsed)
            if len(batch) < _PAGE:
                break
            offset += _PAGE
            if offset >= 2000:
                break
    return rows


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
                FROM dbo.ICLOW WITH (NOLOCK)
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


_SUPPLIER_LIMIT = 12


def supplier_choices(
    history: list[dict[str, Any]],
    *,
    current: str = "",
    current_name: str = "",
    catalog: str = "",
    catalog_name: str = "",
) -> list[dict[str, Any]]:
    """Suppliers a buyer can pick. Recent purchase accounts first, then the catalog vendor."""
    by_acct: dict[str, dict[str, Any]] = {}
    for row in history or []:
        acct = str(row.get("acctno") or "").strip()
        if not acct:
            continue
        try:
            bills = int(row.get("bills") or 0)
        except (TypeError, ValueError):
            bills = 0
        by_acct[acct] = {
            "acctno": acct,
            "name": str(row.get("name") or "").strip(),
            "bills": bills,
            "last_date": str(row.get("last_date") or "")[:10],
        }
    for acct, name in ((catalog, catalog_name), (current, current_name)):
        code = str(acct or "").strip()
        if not code:
            continue
        label = str(name or "").strip()
        if code not in by_acct:
            by_acct[code] = {"acctno": code, "name": label, "bills": 0, "last_date": ""}
        elif label and not by_acct[code]["name"]:
            by_acct[code]["name"] = label
    rows = list(by_acct.values())
    rows.sort(key=lambda row: (row["last_date"], row["bills"], row["acctno"]), reverse=True)
    kept = rows[:_SUPPLIER_LIMIT]
    current_code = str(current or "").strip()
    if current_code and current_code not in {row["acctno"] for row in kept}:
        kept.append(by_acct[current_code])
    return kept


def fetch_bcode_suppliers(
    bcodes: list[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, str]]]:
    """Purchase-invoice suppliers and the ICMAS catalog vendor, keyed by product code."""
    codes = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    history: dict[str, list[dict[str, Any]]] = {}
    catalog: dict[str, dict[str, str]] = {}
    if not codes:
        return history, catalog
    engine = get_site_engine("hq")
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"b{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":b{n}" for n in range(len(chunk)))
            hist_sql = text(
                f"""
                SELECT
                  {_NV('d.BCODE', 40)} AS BCODE,
                  {_NV('d.ACCTNO', 40)} AS ACCTNO,
                  MAX({_NV('a.ACCTNAME', 200)}) AS ACCTNAME,
                  COUNT(*) AS BILLS,
                  CONVERT(varchar(10), MAX(d.BILLDATE), 23) AS LAST_DATE
                FROM dbo.PIDET d WITH (NOLOCK)
                LEFT JOIN dbo.APMAS a WITH (NOLOCK)
                  ON {_NV('a.ACCTNO', 40)} = {_NV('d.ACCTNO', 40)}
                WHERE {_NV('d.BCODE', 40)} IN ({placeholders})
                  AND {_NV('d.ACCTNO', 40)} <> ''
                  AND UPPER({_NV('d.CANCELED', 10)}) <> 'Y'
                  AND {_NV('d.JOURMODE', 10)} <> '0'
                GROUP BY {_NV('d.BCODE', 40)}, {_NV('d.ACCTNO', 40)}
                """
            )
            for row in conn.execute(hist_sql, params).mappings().all():
                bcode = str(row.get("BCODE") or "").strip()
                acct = str(row.get("ACCTNO") or "").strip()
                if not bcode or not acct:
                    continue
                history.setdefault(bcode, []).append(
                    {
                        "acctno": acct,
                        "name": str(row.get("ACCTNAME") or "").strip(),
                        "bills": row.get("BILLS"),
                        "last_date": str(row.get("LAST_DATE") or "")[:10],
                    }
                )
            cat_sql = text(
                f"""
                SELECT
                  {_NV('i.BCODE', 40)} AS BCODE,
                  {_NV('i.VENDOR', 40)} AS VENDOR,
                  {_NV('a.ACCTNAME', 200)} AS ACCTNAME
                FROM dbo.ICMAS i WITH (NOLOCK)
                LEFT JOIN dbo.APMAS a WITH (NOLOCK)
                  ON {_NV('a.ACCTNO', 40)} = {_NV('i.VENDOR', 40)}
                WHERE {_NV('i.BCODE', 40)} IN ({placeholders})
                """
            )
            for row in conn.execute(cat_sql, params).mappings().all():
                bcode = str(row.get("BCODE") or "").strip()
                acct = str(row.get("VENDOR") or "").strip()
                if bcode and acct:
                    catalog[bcode] = {
                        "acctno": acct,
                        "name": str(row.get("ACCTNAME") or "").strip(),
                    }
    return history, catalog


def fetch_vendor_cards(acctnos: list[str]) -> dict[str, dict[str, str]]:
    """APMAS card used on the vendor sheet. MOBILE is the tax id in PARTS9."""
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
    out: dict[str, dict[str, str]] = {}
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"a{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":a{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT
                  LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR1,'')))) AS ADDR1,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR2,'')))) AS ADDR2,
                  LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PHONE,'')))) AS PHONE,
                  LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MOBILE,'')))) AS MOBILE,
                  LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(FAX,'')))) AS FAX,
                  LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(CONTACT,'')))) AS CONTACT,
                  LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(CONVERT(varchar(40), TERM), '')))) AS TERM
                FROM dbo.APMAS
                WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) IN ({placeholders})
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                acct = str(row.get("ACCTNO") or "").strip()
                if not acct:
                    continue
                out[acct] = {
                    "acctno": acct,
                    "name": str(row.get("ACCTNAME") or "").strip(),
                    "addr1": str(row.get("ADDR1") or "").strip(),
                    "addr2": str(row.get("ADDR2") or "").strip(),
                    "phone": str(row.get("PHONE") or "").strip(),
                    "tax_id": str(row.get("MOBILE") or "").strip(),
                    "fax": str(row.get("FAX") or "").strip(),
                    "contact": str(row.get("CONTACT") or "").strip(),
                    "term": str(row.get("TERM") or "").strip(),
                }
    return out


def fetch_sheet_products(bcodes: list[str]) -> dict[str, dict[str, Any]]:
    """HQ ICMAS identity and money fields. Sell price is PRICE1; cost is COSTLAST / COSTNET."""
    codes = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw or "").strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    if not codes:
        return {}
    engine = get_site_engine("hq")
    out: dict[str, dict[str, Any]] = {}
    with engine.connect() as conn:
        for start in range(0, len(codes), 80):
            chunk = codes[start : start + 80]
            params = {f"b{n}": code for n, code in enumerate(chunk)}
            placeholders = ", ".join(f":b{n}" for n in range(len(chunk)))
            sql = text(
                f"""
                SELECT
                  LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
                  LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DESCR,'')))) AS DESCR,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(MODEL,'')))) AS MODEL,
                  LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(BRAND,'')))) AS BRAND,
                  LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) AS PCODE,
                  LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) AS MCODE,
                  LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(UI1,'')))) AS UI1,
                  LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(UI2,'')))) AS UI2,
                  MTP2,
                  PRICE1, COSTLAST, COSTNET
                FROM dbo.ICMAS
                WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                bcode = str(row.get("BCODE") or "").strip()
                if not bcode:
                    continue
                out[bcode] = {
                    "descr": str(row.get("DESCR") or "").strip(),
                    "model": str(row.get("MODEL") or "").strip(),
                    "brand": str(row.get("BRAND") or "").strip(),
                    "pcode": str(row.get("PCODE") or "").strip(),
                    "mcode": str(row.get("MCODE") or "").strip(),
                    "ui": str(row.get("UI1") or "").strip(),
                    "ui2": str(row.get("UI2") or "").strip(),
                    "mtp2": row.get("MTP2"),
                    "price1": row.get("PRICE1"),
                    "costlast": row.get("COSTLAST"),
                    "costnet": row.get("COSTNET"),
                }
    return out


def search_products(query: str, *, limit: int = 12) -> list[dict[str, Any]]:
    """HQ ICMAS rows matching a code, genuine number, factory number, or name."""
    q = str(query or "").strip()
    if len(q) < 2:
        return []
    safe = q.replace("%", "").replace("_", "").replace("[", "")
    if len(safe) < 2:
        return []
    engine = get_site_engine("hq")
    name_ok = 1 if len(safe) >= 3 else 0
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
          LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DESCR,'')))) AS DESCR,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(MODEL,'')))) AS MODEL,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(BRAND,'')))) AS BRAND,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) AS PCODE,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) AS MCODE,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(UI1,'')))) AS UI1,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(UI2,'')))) AS UI2,
          MTP2,
          PRICE1, COSTLAST, COSTNET,
          LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(VENDOR,'')))) AS VENDOR,
          QTYOH2
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE (
            LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :q
            OR LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) LIKE :prefix
            OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) = :q
            OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) LIKE :prefix
            OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) = :q
            OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) LIKE :prefix
            OR (
              :name_ok = 1 AND (
                LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DESCR,'')))) LIKE :contains
                OR LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(MODEL,'')))) LIKE :contains
                OR LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(BRAND,'')))) LIKE :contains
                OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) LIKE :contains
                OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) LIKE :contains
              )
            )
          )
        ORDER BY
          CASE
            WHEN LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :q THEN 0
            WHEN LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) LIKE :prefix THEN 1
            WHEN LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) = :q
              OR LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) = :q THEN 2
            ELSE 3
          END,
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE)))
        """
    )
    out: list[dict[str, Any]] = []
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "lim": int(limit),
                "q": safe,
                "prefix": safe + "%",
                "name_ok": name_ok,
                "contains": f"%{safe}%",
            },
        ).mappings().all()
    for row in rows:
        bcode = str(row.get("BCODE") or "").strip()
        if not bcode:
            continue
        out.append(
            {
                "bcode": bcode,
                "descr": str(row.get("DESCR") or "").strip(),
                "model": str(row.get("MODEL") or "").strip(),
                "brand": str(row.get("BRAND") or "").strip(),
                "pcode": str(row.get("PCODE") or "").strip(),
                "mcode": str(row.get("MCODE") or "").strip(),
                "ui": str(row.get("UI1") or "").strip(),
                "ui2": str(row.get("UI2") or "").strip(),
                "mtp2": row.get("MTP2"),
                "price1": row.get("PRICE1"),
                "costlast": row.get("COSTLAST"),
                "costnet": row.get("COSTNET"),
                "vendor": str(row.get("VENDOR") or "").strip(),
                "qtyoh2": row.get("QTYOH2"),
            }
        )
    return out


def search_vendors(query: str, *, limit: int = 8) -> list[dict[str, str]]:
    """HQ APMAS accounts matching a short code or a longer name."""
    q = str(query or "").strip()
    if len(q) < 2:
        return []
    safe = q.replace("%", "").replace("_", "").replace("[", "")
    if len(safe) < 2:
        return []
    engine = get_site_engine("hq")
    name_ok = 1 if len(safe) >= 3 else 0
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME
        FROM dbo.APMAS WITH (NOLOCK)
        WHERE UPPER(LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,''))))) <> 'Y'
          AND (
            LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :q
            OR LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) LIKE :prefix
            OR (:name_ok = 1 AND LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) LIKE :contains)
          )
        ORDER BY
          CASE
            WHEN LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :q THEN 0
            WHEN LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) LIKE :prefix THEN 1
            ELSE 2
          END,
          LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO)))
        """
    )
    out: list[dict[str, str]] = []
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "lim": int(limit),
                "q": safe,
                "prefix": safe + "%",
                "name_ok": name_ok,
                "contains": f"%{safe}%",
            },
        ).mappings().all()
    for row in rows:
        acct = str(row.get("ACCTNO") or "").strip()
        if not acct:
            continue
        out.append({"acctno": acct, "name": str(row.get("ACCTNAME") or "").strip()})
    return out


def fetch_ordered_product_rows(acctno: str, *, limit: int = 80) -> list[dict[str, Any]]:
    """Distinct products purchased from one HQ vendor, newest bill first."""
    acct = str(acctno or "").strip()
    if not acct:
        return []
    engine = get_site_engine("hq")
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
          CONVERT(varchar(10), MAX(BILLDATE), 23) AS LAST_DATE,
          COUNT(*) AS BILLS
        FROM dbo.PIDET WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :acct
          AND LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) <> ''
          AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,''))))) <> 'Y'
          AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(JOURMODE,'')))) <> '0'
        GROUP BY LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE)))
        ORDER BY MAX(BILLDATE) DESC
        """
    )
    out: list[dict[str, Any]] = []
    with engine.connect() as conn:
        rows = conn.execute(sql, {"lim": int(limit), "acct": acct}).mappings().all()
    for row in rows:
        bcode = str(row.get("BCODE") or "").strip()
        if not bcode:
            continue
        try:
            bills = int(row.get("BILLS") or 0)
        except (TypeError, ValueError):
            bills = 0
        out.append(
            {
                "bcode": bcode,
                "last_date": str(row.get("LAST_DATE") or "")[:10],
                "bills": bills,
            }
        )
    return out


def fetch_live_vendors(acctnos: list[str]) -> dict[str, str]:
    """Non-canceled APMAS accounts. An empty name still means the account exists."""
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
                FROM dbo.APMAS WITH (NOLOCK)
                WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) IN ({placeholders})
                  AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,''))))) <> 'Y'
                """
            )
            for row in conn.execute(sql, params).mappings().all():
                acct = str(row.get("ACCTNO") or "").strip()
                if acct:
                    out[acct] = str(row.get("ACCTNAME") or "").strip()
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
