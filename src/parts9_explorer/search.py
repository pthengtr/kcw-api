from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.db import get_site_engine
from src.parts9_explorer.query import category_label, code1_label, parse_query, size_labels

PRODUCT_COLS = """
  LTRIM(RTRIM(BCODE)) AS BCODE,
  LTRIM(RTRIM(COALESCE(DESCR,''))) AS DESCR,
  LTRIM(RTRIM(COALESCE(PCODE,''))) AS PCODE,
  LTRIM(RTRIM(COALESCE(MCODE,''))) AS MCODE,
  LTRIM(RTRIM(COALESCE(BRAND,''))) AS BRAND,
  LTRIM(RTRIM(COALESCE(MODEL,''))) AS MODEL,
  UPPER(LTRIM(RTRIM(COALESCE(CODE1,'')))) AS CODE1,
  LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE1), ''))) AS SIZE1,
  LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE2), ''))) AS SIZE2,
  LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE3), ''))) AS SIZE3,
  LTRIM(RTRIM(COALESCE(UI1,''))) AS UI1,
  LTRIM(RTRIM(COALESCE(UI2,''))) AS UI2,
  MTP2, QTYOH2, QTYMIN,
  PRICE1, PRICE2, PRICE3, PRICE4, PRICE5,
  PRICEM1, PRICEM2, PRICEM3, PRICEM4, PRICEM5,
  LTRIM(RTRIM(COALESCE(LOCATION1,''))) AS LOCATION1,
  LTRIM(RTRIM(COALESCE(LOCATION2,''))) AS LOCATION2,
  LTRIM(RTRIM(COALESCE(CANCELED,''))) AS CANCELED
"""


def _num(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    if n == 0:
        return None
    return n


def _price_map(row: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for i in range(1, 6):
        p = _num(row.get(f"PRICE{i}"))
        if p is not None:
            out[f"PRICE{i}"] = p
        m = _num(row.get(f"PRICEM{i}"))
        if m is not None:
            out[f"PRICEM{i}"] = m
    return out


def product_image_urls(bcode: str) -> list[str]:
    settings = get_explorer_settings()
    root = (settings.supabase_url or "").rstrip("/")
    bucket = settings.supabase_image_bucket or "pictures"
    folder = (settings.supabase_image_base_folder or "product").strip("/")
    code = (bcode or "").strip()
    if not root or not code:
        return []
    names = [f"{code}.jpg"] + [f"{code}_{i}.jpg" for i in range(2, 6)]
    return [f"{root}/storage/v1/object/public/{bucket}/{folder}/{code}/{name}" for name in names]


def _serialize_product(row: dict, *, site: str) -> dict[str, Any]:
    bcode = str(row.get("BCODE") or "").strip()
    code1 = str(row.get("CODE1") or "").strip().upper() or None
    s1, s2, s3 = size_labels(code1)
    qtymin = _num(row.get("QTYMIN")) or 0.0
    qty = _num(row.get("QTYOH2"))
    return {
        "site": site.upper(),
        "bcode": bcode,
        "descr": str(row.get("DESCR") or "").strip(),
        "pcode": str(row.get("PCODE") or "").strip(),
        "mcode": str(row.get("MCODE") or "").strip(),
        "brand": str(row.get("BRAND") or "").strip(),
        "model": str(row.get("MODEL") or "").strip(),
        "code1": code1,
        "code1_label": code1_label(code1),
        "category": category_label(bcode),
        "size1": str(row.get("SIZE1") or "").strip(),
        "size2": str(row.get("SIZE2") or "").strip(),
        "size3": str(row.get("SIZE3") or "").strip(),
        "size_labels": {"size1": s1, "size2": s2, "size3": s3},
        "ui1": str(row.get("UI1") or "").strip(),
        "ui2": str(row.get("UI2") or "").strip(),
        "mtp2": _num(row.get("MTP2")),
        "qtyoh2": qty if qty is not None else 0.0,
        "qtymin": qtymin,
        "do_not_restock": qtymin < 0,
        "location1": str(row.get("LOCATION1") or "").strip(),
        "location2": str(row.get("LOCATION2") or "").strip(),
        "prices": _price_map(row),
        "photos": product_image_urls(bcode),
    }


def search_products(raw: str, *, site: str, include_skip: bool = False, limit: int = 50):
    parsed = parse_query(raw)
    site_key = (site or "hq").strip().lower()
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        return [], f"{site_key.upper()} SQL: {exc}"
    where = ["UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'"]
    params: dict[str, Any] = {}
    if not include_skip:
        where.append(
            "(QTYMIN IS NULL OR ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYMIN), ',', '')) = 0"
            " OR CONVERT(float, REPLACE(CONVERT(varchar(50), QTYMIN), ',', '')) >= 0)"
        )
    if parsed.bcode_prefix:
        where.append("LTRIM(RTRIM(BCODE)) LIKE :bpre")
        params["bpre"] = parsed.bcode_prefix + "%"
    if parsed.code1:
        where.append("UPPER(LTRIM(RTRIM(COALESCE(CODE1,'')))) = :code1")
        params["code1"] = parsed.code1
    for i, sz in enumerate(parsed.sizes, start=1):
        where.append(
            f"LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE{i}), ''))) LIKE :sz{i}"
        )
        params[f"sz{i}"] = f"%{sz}%"
    for i, term in enumerate(parsed.text_terms):
        key = f"t{i}"
        where.append(
            f"(DESCR LIKE :{key} OR PCODE LIKE :{key} OR MCODE LIKE :{key}"
            f" OR BRAND LIKE :{key} OR MODEL LIKE :{key} OR BCODE LIKE :{key})"
        )
        params[key] = f"%{term}%"
    if not parsed.bcode_prefix and not parsed.code1 and not parsed.sizes and not parsed.text_terms:
        if parsed.raw:
            where.append("(DESCR LIKE :q OR PCODE LIKE :q OR MCODE LIKE :q OR BCODE LIKE :q)")
            params["q"] = f"%{parsed.raw}%"
        else:
            return [], None
    top_n = max(1, min(int(limit), 50))
    sql = text(
        f"SELECT TOP {top_n} {PRODUCT_COLS} FROM dbo.ICMAS WHERE "
        + " AND ".join(where)
        + " ORDER BY CASE WHEN LTRIM(RTRIM(BCODE)) = :exact THEN 0"
        " WHEN LTRIM(RTRIM(BCODE)) LIKE :pre THEN 1 ELSE 2 END, BCODE"
    )
    params["exact"] = parsed.raw.strip()
    params["pre"] = (parsed.bcode_prefix or parsed.raw.strip()) + "%"
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:
        return [], str(exc)
    return [_serialize_product(dict(r), site=site_key) for r in rows], None


def get_product(bcode: str, *, site: str):
    code = (bcode or "").strip()
    if not code:
        return None, None
    site_key = (site or "hq").strip().lower()
    try:
        engine = get_site_engine(site_key)
        sql = text(f"SELECT {PRODUCT_COLS} FROM dbo.ICMAS WHERE LTRIM(RTRIM(BCODE)) = :bcode")
        with engine.connect() as conn:
            row = conn.execute(sql, {"bcode": code}).mappings().first()
    except Exception as exc:
        return None, str(exc)
    if not row:
        return None, None
    return _serialize_product(dict(row), site=site_key), None


def _header_lines(engine, header_sql: str, line_sql: str, key: str, value: str):
    with engine.connect() as conn:
        header = conn.execute(text(header_sql), {"q": value}).mappings().first()
        if not header:
            return None
        lines = conn.execute(text(line_sql), {"q": value}).mappings().all()
    return {
        "kind": key,
        "header": {k: ("" if v is None else str(v).strip()) for k, v in dict(header).items()},
        "lines": [{k: ("" if v is None else str(v).strip()) for k, v in dict(r).items()} for r in lines[:200]],
    }


def lookup_document(raw: str, *, site: str):
    parsed = parse_query(raw)
    docno = (parsed.docno or parsed.raw or "").strip()
    if not docno:
        return None, None
    site_key = (site or "hq").strip().lower()
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        return None, str(exc)
    attempts = [
        ("sales",
         "SELECT TOP 1 BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, PAID, CASHED, SALE FROM dbo.SIMAS WHERE LTRIM(RTRIM(BILLNO)) = :q",
         "SELECT TOP 200 LINE, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT FROM dbo.SIDET WHERE LTRIM(RTRIM(BILLNO)) = :q ORDER BY LINE"),
        ("po",
         "SELECT TOP 1 DOCNO, DOCDATE, ACCTNO, ACCTNAME, AFTERTAX FROM dbo.POMAS WHERE LTRIM(RTRIM(DOCNO)) = :q",
         "SELECT TOP 200 LINE, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT FROM dbo.PODET WHERE LTRIM(RTRIM(DOCNO)) = :q ORDER BY LINE"),
        ("pv",
         "SELECT TOP 1 VOUCNO, VOUCDATE, ACCTNO, ACCTNAME, BILLAMT, CHKAMT FROM dbo.PVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q",
         "SELECT TOP 1 VOUCNO FROM dbo.PVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q"),
        ("rv",
         "SELECT TOP 1 VOUCNO, VOUCDATE, ACCTNO, ACCTNAME FROM dbo.RVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q",
         "SELECT TOP 1 VOUCNO FROM dbo.RVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q"),
    ]
    last_err = None
    for kind, hsql, lsql in attempts:
        try:
            found = _header_lines(engine, hsql, lsql, kind, docno)
        except Exception as exc:
            last_err = str(exc)
            continue
        if found:
            found["site"] = site_key.upper()
            return found, None
    return None, last_err


def recent_for_product(bcode: str, *, site: str, limit: int = 15) -> dict[str, Any]:
    code = (bcode or "").strip()
    site_key = (site or "hq").strip().lower()
    out: dict[str, Any] = {"sales": [], "po": [], "iclow": [], "error": None}
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        out["error"] = str(exc)
        return out
    queries = {
        "sales": "SELECT TOP 15 BILLNO, BILLDATE, QTY, UI, PRICE, AMOUNT FROM dbo.SIDET WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY BILLDATE DESC",
        "po": "SELECT TOP 15 DOCNO, DOCDATE, QTY, UI, PRICE, AMOUNT FROM dbo.PODET WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY DOCDATE DESC",
        "iclow": "SELECT TOP 15 DOCNO, DOCDATE, ORDERED, RECEIVED, CANCELED, BCODE FROM dbo.ICLOW WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY DOCDATE DESC",
    }
    with engine.connect() as conn:
        for key, sql in queries.items():
            try:
                rows = conn.execute(text(sql), {"bcode": code}).mappings().all()
                out[key] = [{k: ("" if v is None else str(v).strip()) for k, v in dict(r).items()} for r in rows]
            except Exception as exc:
                out[key] = []
                out["error"] = (out.get("error") or "") + f" {key}:{exc}"
    return out


def probe_sites() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for site in ("hq", "syp"):
        try:
            engine = get_site_engine(site)
            with engine.connect() as conn:
                row = conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS db_name")).mappings().first()
            result[site] = {
                "ok": True,
                "server": str(row["server_name"] if row else ""),
                "db": str(row["db_name"] if row else ""),
            }
        except Exception as exc:
            result[site] = {"ok": False, "error": str(exc)}
    return result
