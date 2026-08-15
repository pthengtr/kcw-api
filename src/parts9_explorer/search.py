from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.db import get_site_engine
from src.parts9_explorer.query import (
    DOC_KIND_LABELS,
    category_label,
    code1_label,
    infer_doc_kind,
    parse_query,
    size_labels,
)

_PI_HEADER_COLS = (
    "BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, PAID, CASHAMT, CHKAMT, "
    "PO, BILLTYPE, CANCELED, REMARKS, NOTENO, NOTEDATE, VOUCNO1, VOUCNO2"
)
_PV_HEADER_COLS = (
    "JOURTYPE, VOUCED, VOUCDATE, VOUCNO, NOTED, NOTEDATE, NOTENO, RCPTNO, "
    "ACCTNO, ACCTNAME, BILLCNT, BILLAMT, CHKAMT, CASHAMT, NETAMT, PAYAMT, PAID, CANCELED"
)

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


def _row(mapping) -> dict[str, str]:
    return {k: ("" if v is None else str(v).strip()) for k, v in dict(mapping).items()}


def _rows(mappings, limit: int = 200) -> list[dict[str, str]]:
    return [_row(r) for r in mappings[:limit]]


def _amt_sql(col: str) -> str:
    return (
        f"CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(50), {col}), ',', '')) = 1 "
        f"THEN CONVERT(float, REPLACE(CONVERT(varchar(50), {col}), ',', '')) ELSE 0 END"
    )


_DOC_SPECS: dict[str, dict[str, str]] = {
    "si": {
        "header": (
            "SELECT TOP 12 BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, PAID, CASHED, SALE, "
            "CANCELED FROM dbo.SIMAS WHERE LTRIM(RTRIM(BILLNO)) = :q "
            "OR LTRIM(RTRIM(BILLNO)) LIKE :pre ORDER BY CASE WHEN LTRIM(RTRIM(BILLNO)) = :q THEN 0 ELSE 1 END, BILLDATE DESC"
        ),
        "lines": (
            "SELECT TOP 200 LINE, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT FROM dbo.SIDET "
            "WHERE LTRIM(RTRIM(BILLNO)) = :q ORDER BY LINE"
        ),
        "no": "BILLNO",
    },
    "pi": {
        "header": (
            f"SELECT TOP 12 {_PI_HEADER_COLS} FROM dbo.PIMAS WHERE LTRIM(RTRIM(BILLNO)) = :q "
            "OR LTRIM(RTRIM(BILLNO)) LIKE :pre "
            "OR LTRIM(RTRIM(COALESCE(PO,''))) = :q "
            "OR LTRIM(RTRIM(COALESCE(NOTENO,''))) = :q "
            "OR LTRIM(RTRIM(COALESCE(NOTENO,''))) LIKE :pre "
            "OR LTRIM(RTRIM(COALESCE(VOUCNO1,''))) = :q "
            "OR LTRIM(RTRIM(COALESCE(VOUCNO2,''))) = :q "
            "ORDER BY CASE WHEN LTRIM(RTRIM(BILLNO)) = :q THEN 0 "
            "WHEN LTRIM(RTRIM(COALESCE(NOTENO,''))) = :q THEN 1 ELSE 2 END, BILLDATE DESC"
        ),
        "lines": (
            "SELECT TOP 200 LINE, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT, BILLTYPE FROM dbo.PIDET "
            "WHERE LTRIM(RTRIM(BILLNO)) = :q ORDER BY LINE"
        ),
        "no": "BILLNO",
    },
    "po": {
        "header": (
            "SELECT TOP 12 DOCNO, DOCDATE, ACCTNO, ACCTNAME, AFTERTAX, BILLED, BILLNO, BILLDATE, "
            "CANCELED, REMARKS FROM dbo.POMAS WHERE LTRIM(RTRIM(DOCNO)) = :q "
            "OR LTRIM(RTRIM(DOCNO)) LIKE :pre ORDER BY CASE WHEN LTRIM(RTRIM(DOCNO)) = :q THEN 0 ELSE 1 END, DOCDATE DESC"
        ),
        "lines": (
            "SELECT TOP 200 LINE, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT FROM dbo.PODET "
            "WHERE LTRIM(RTRIM(DOCNO)) = :q ORDER BY LINE"
        ),
        "no": "DOCNO",
    },
    "pv": {
        "header": (
            f"SELECT TOP 12 {_PV_HEADER_COLS} FROM dbo.PVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q "
            "OR LTRIM(RTRIM(VOUCNO)) LIKE :pre OR LTRIM(RTRIM(COALESCE(RCPTNO,''))) = :q "
            "OR LTRIM(RTRIM(COALESCE(NOTENO,''))) = :q "
            "OR LTRIM(RTRIM(COALESCE(NOTENO,''))) LIKE :pre "
            "ORDER BY CASE WHEN LTRIM(RTRIM(VOUCNO)) = :q THEN 0 "
            "WHEN LTRIM(RTRIM(COALESCE(NOTENO,''))) = :q THEN 1 ELSE 2 END, "
            "COALESCE(VOUCDATE, NOTEDATE) DESC"
        ),
        "lines": (
            "SELECT TOP 80 VOUCDATE, VOUCNO, ACCTNO, CHKNO, CHKDATE, CHKAMT, BANKNAME, PAYTYPE, STATUS "
            "FROM dbo.BPDET WHERE LTRIM(RTRIM(VOUCNO)) = :q ORDER BY CHKDATE"
        ),
        "no": "VOUCNO",
    },
    "rv": {
        "header": (
            "SELECT TOP 12 VOUCNO, VOUCDATE, ACCTNO, ACCTNAME, BILLAMT, CHKAMT, CASHAMT, NETAMT, "
            "PAYAMT, PAID, RCPTNO, CANCELED FROM dbo.RVMAS WHERE LTRIM(RTRIM(VOUCNO)) = :q "
            "OR LTRIM(RTRIM(VOUCNO)) LIKE :pre OR LTRIM(RTRIM(COALESCE(RCPTNO,''))) = :q "
            "ORDER BY CASE WHEN LTRIM(RTRIM(VOUCNO)) = :q THEN 0 ELSE 1 END, VOUCDATE DESC"
        ),
        "lines": (
            "SELECT TOP 80 VOUCDATE, VOUCNO, ACCTNO, CARDNAME, CHKNO, CHKDATE, CHKAMT, BANKNAME, PAYTYPE, STATUS "
            "FROM dbo.BRDET WHERE LTRIM(RTRIM(VOUCNO)) = :q ORDER BY CHKDATE"
        ),
        "no": "VOUCNO",
    },
}


def _pack_doc(kind: str, site: str, header: dict, lines: list[dict], extra: dict | None = None) -> dict[str, Any]:
    no_key = _DOC_SPECS.get(kind, {}).get("no", "DOCNO")
    docno = header.get(no_key) or header.get("BILLNO") or header.get("DOCNO") or header.get("VOUCNO") or ""
    label = DOC_KIND_LABELS.get(kind, kind.upper())
    if kind == "pv" and not (header.get("VOUCNO") or "").strip() and (header.get("NOTENO") or "").strip():
        docno = header.get("NOTENO") or docno
        label = "โน้ตจ่าย NP"
    packed = {
        "kind": kind,
        "kind_label": label,
        "site": site.upper(),
        "docno": docno,
        "header": header,
        "lines": lines,
    }
    if extra:
        packed.update(extra)
    return packed


def _or_equals(col: str, key: str) -> str:
    return f"LTRIM(RTRIM(COALESCE({col},''))) = :{key}"


def _related_pi_headers(conn, *, note: str, vouc: str) -> list[dict[str, str]]:
    note = (note or "").strip()
    vouc = (vouc or "").strip()
    clauses: list[str] = []
    params: dict[str, str] = {}
    if note:
        clauses.append(_or_equals("NOTENO", "note"))
        clauses.append("LTRIM(RTRIM(BILLNO)) = :note")
        params["note"] = note
    if vouc:
        clauses.append(_or_equals("VOUCNO1", "vouc"))
        clauses.append(_or_equals("VOUCNO2", "vouc"))
        params["vouc"] = vouc
    if not clauses:
        return []
    sql = text(
        f"SELECT TOP 80 {_PI_HEADER_COLS} FROM dbo.PIMAS WHERE "
        + " OR ".join(clauses)
        + " ORDER BY BILLDATE DESC"
    )
    return [_row(r) for r in conn.execute(sql, params).mappings().all()]


def _related_pv_headers(conn, *, note: str, voucs: list[str]) -> list[dict[str, str]]:
    note = (note or "").strip()
    voucs = [v.strip() for v in voucs if (v or "").strip()]
    clauses: list[str] = []
    params: dict[str, str] = {}
    if note:
        clauses.append(_or_equals("NOTENO", "note"))
        params["note"] = note
    for i, vouc in enumerate(voucs):
        key = f"vouc{i}"
        clauses.append(_or_equals("VOUCNO", key))
        params[key] = vouc
    if not clauses:
        return []
    sql = text(
        f"SELECT TOP 12 {_PV_HEADER_COLS} FROM dbo.PVMAS WHERE "
        + " OR ".join(clauses)
        + " ORDER BY COALESCE(VOUCDATE, NOTEDATE) DESC"
    )
    return [_row(r) for r in conn.execute(sql, params).mappings().all()]


def _pi_lines(conn, billno: str) -> list[dict[str, str]]:
    if not (billno or "").strip():
        return []
    try:
        return _rows(
            conn.execute(text(_DOC_SPECS["pi"]["lines"]), {"q": billno.strip()}).mappings().all()
        )
    except Exception:
        return []


def _fetch_kind(engine, kind: str, value: str, site: str) -> list[dict[str, Any]]:
    spec = _DOC_SPECS[kind]
    params = {"q": value, "pre": value + "%"}
    with engine.connect() as conn:
        headers = conn.execute(text(spec["header"]), params).mappings().all()
        if not headers:
            return []
        out = []
        for h in headers:
            header = _row(h)
            docno = header.get(spec["no"]) or value
            line_q = docno
            if kind == "pv":
                line_q = (header.get("VOUCNO") or "").strip()
            try:
                lines = (
                    _rows(conn.execute(text(spec["lines"]), {"q": line_q}).mappings().all())
                    if line_q
                    else []
                )
            except Exception:
                lines = []
            extra: dict[str, Any] = {}
            if kind == "po":
                extra["iclow"] = _iclow_for_docno(conn, docno)
            if kind == "pi":
                if header.get("PO"):
                    extra["po"] = header.get("PO")
                extra["vouchers"] = [
                    _pack_doc("pv", site, pv, [])
                    for pv in _related_pv_headers(
                        conn,
                        note=header.get("NOTENO") or "",
                        voucs=[header.get("VOUCNO1") or "", header.get("VOUCNO2") or ""],
                    )
                ]
            if kind == "pv":
                extra["bills"] = [
                    _pack_doc("pi", site, pi, _pi_lines(conn, pi.get("BILLNO") or ""), {"po": pi.get("PO")} if pi.get("PO") else None)
                    for pi in _related_pi_headers(
                        conn, note=header.get("NOTENO") or "", vouc=header.get("VOUCNO") or ""
                    )
                ]
            out.append(_pack_doc(kind, site, header, lines, extra or None))
        return out


def lookup_documents(
    raw: str,
    *,
    site: str,
    kind: str | None = None,
    kinds: tuple[str, ...] | None = None,
):
    parsed = parse_query(raw)
    docno = (parsed.docno or parsed.raw or "").strip()
    site_key = (site or "hq").strip().lower()
    forced = (kind or parsed.doc_kind or "").strip().lower()
    if forced in ("all", "product", ""):
        forced = parsed.doc_kind or infer_doc_kind(docno) or ""
    if forced == "iclow":
        if not docno:
            return [], None
        try:
            engine = get_site_engine(site_key)
        except Exception as exc:
            return [], str(exc)
        return _lookup_iclow(engine, docno, site_key)
    if not docno:
        return [], None
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        return [], str(exc)
    if kinds:
        order = [k for k in kinds if k in _DOC_SPECS]
        stop_first = False
    elif forced in _DOC_SPECS:
        order = [forced]
        stop_first = True
    else:
        order = ["si", "pi", "po", "pv", "rv"]
        stop_first = False
    last_err = None
    found: list[dict[str, Any]] = []
    for k in order:
        try:
            rows = _fetch_kind(engine, k, docno, site_key)
        except Exception as exc:
            last_err = str(exc)
            continue
        found.extend(rows)
        if found and stop_first:
            break
    return found, (None if found else last_err)


def lookup_document(raw: str, *, site: str):
    docs, err = lookup_documents(raw, site=site)
    return (docs[0] if docs else None), err


def _iclow_status(row: dict) -> str:
    if str(row.get("CANCELED") or "").upper() == "Y":
        return "canceled"
    ordered = str(row.get("ORDERED") or "").upper() == "Y"
    received = str(row.get("RECEIVED") or "").upper() == "Y"
    if ordered and not received:
        return "pending"
    if received:
        return "received"
    return "to_order"


def _iclow_for_docno(conn, docno: str) -> dict[str, Any]:
    sql = text(
        "SELECT TOP 200 DOCNO, DOCDATE, VENDOR, BCODE, DESCR, QTY, UI, PRICE, AMOUNT, "
        "ORDERED, RECEIVED, CANCELED, RCVDDATE, RCVDNO FROM dbo.ICLOW "
        "WHERE LTRIM(RTRIM(DOCNO)) = :q ORDER BY BCODE"
    )
    lines = [_row(r) for r in conn.execute(sql, {"q": docno}).mappings().all()]
    counts = {"pending": 0, "received": 0, "canceled": 0, "to_order": 0}
    for line in lines:
        counts[_iclow_status(line)] += 1
        line["status"] = _iclow_status(line)
    return {"counts": counts, "lines": lines}


def _lookup_iclow(engine, q: str, site: str):
    like = f"%{q}%"
    sql = text(
        "SELECT TOP 80 DOCNO, DOCDATE, VENDOR, BCODE, DESCR, QTY, UI, PRICE, AMOUNT, "
        "ORDERED, RECEIVED, CANCELED, RCVDDATE, RCVDNO FROM dbo.ICLOW WHERE "
        "LTRIM(RTRIM(COALESCE(DOCNO,''))) LIKE :like "
        "OR LTRIM(RTRIM(COALESCE(BCODE,''))) LIKE :like "
        "OR LTRIM(RTRIM(COALESCE(VENDOR,''))) LIKE :like "
        "OR LTRIM(RTRIM(COALESCE(DESCR,''))) LIKE :like "
        "OR LTRIM(RTRIM(COALESCE(RCVDNO,''))) LIKE :like "
        "ORDER BY DOCDATE DESC"
    )
    try:
        with engine.connect() as conn:
            lines = [_row(r) for r in conn.execute(sql, {"like": like}).mappings().all()]
    except Exception as exc:
        return [], str(exc)
    groups: dict[str, dict[str, Any]] = {}
    for line in lines:
        st = _iclow_status(line)
        line["status"] = st
        doc = line.get("DOCNO") or "(ไม่มีเลข PO)"
        g = groups.setdefault(
            doc,
            {
                "kind": "iclow",
                "kind_label": DOC_KIND_LABELS["iclow"],
                "site": site.upper(),
                "docno": doc,
                "header": {
                    "DOCNO": doc,
                    "DOCDATE": line.get("DOCDATE") or "",
                    "VENDOR": line.get("VENDOR") or "",
                },
                "lines": [],
                "iclow": {"counts": {"pending": 0, "received": 0, "canceled": 0, "to_order": 0}, "lines": []},
            },
        )
        g["lines"].append(line)
        g["iclow"]["lines"].append(line)
        g["iclow"]["counts"][st] += 1
    return list(groups.values()), None


def iclow_summary(site: str) -> tuple[dict[str, Any] | None, str | None]:
    site_key = (site or "hq").strip().lower()
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        return None, str(exc)
    amt = _amt_sql("AMOUNT")
    pending = "ORDERED = 'Y' AND ISNULL(RECEIVED,'N') = 'N' AND ISNULL(CANCELED,'N') = 'N'"
    totals_sql = text(
        f"""
        SELECT
          COUNT(*) AS total_lines,
          SUM(CASE WHEN {pending} THEN 1 ELSE 0 END) AS pending_lines,
          SUM(CASE WHEN {pending} THEN {amt} ELSE 0 END) AS pending_amount,
          SUM(CASE WHEN UPPER(ISNULL(RECEIVED,'N')) = 'Y' THEN 1 ELSE 0 END) AS received_lines,
          SUM(CASE WHEN UPPER(ISNULL(CANCELED,'N')) = 'Y' THEN 1 ELSE 0 END) AS canceled_lines,
          SUM(CASE WHEN ISNULL(ORDERED,'N') <> 'Y' AND ISNULL(CANCELED,'N') <> 'Y' THEN 1 ELSE 0 END) AS to_order_lines,
          COUNT(DISTINCT CASE WHEN {pending} THEN LTRIM(RTRIM(DOCNO)) END) AS pending_pos
        FROM dbo.ICLOW
        """
    )
    vendors_sql = text(
        f"""
        SELECT TOP 8 LTRIM(RTRIM(i.VENDOR)) AS VENDOR,
               MAX(LTRIM(RTRIM(COALESCE(a.ACCTNAME,'')))) AS ACCTNAME,
               COUNT(*) AS lines,
               SUM({amt}) AS amount
        FROM dbo.ICLOW i
        LEFT JOIN dbo.APMAS a ON LTRIM(RTRIM(a.ACCTNO)) = LTRIM(RTRIM(i.VENDOR))
        WHERE i.ORDERED = 'Y' AND ISNULL(i.RECEIVED,'N') = 'N' AND ISNULL(i.CANCELED,'N') = 'N'
        GROUP BY LTRIM(RTRIM(i.VENDOR))
        ORDER BY COUNT(*) DESC
        """
    )
    recent_sql = text(
        f"""
        SELECT TOP 25 DOCNO, DOCDATE, VENDOR, BCODE, DESCR, QTY, UI, PRICE, AMOUNT
        FROM dbo.ICLOW
        WHERE {pending}
        ORDER BY DOCDATE DESC
        """
    )
    vendors_sql_plain = text(
        f"""
        SELECT TOP 8 LTRIM(RTRIM(VENDOR)) AS VENDOR, '' AS ACCTNAME,
               COUNT(*) AS lines, SUM({amt}) AS amount
        FROM dbo.ICLOW
        WHERE ORDERED = 'Y' AND ISNULL(RECEIVED,'N') = 'N' AND ISNULL(CANCELED,'N') = 'N'
        GROUP BY LTRIM(RTRIM(VENDOR))
        ORDER BY COUNT(*) DESC
        """
    )
    try:
        with engine.connect() as conn:
            totals = _row(conn.execute(totals_sql).mappings().first() or {})
            try:
                vendors = _rows(conn.execute(vendors_sql).mappings().all(), 8)
            except Exception:
                vendors = _rows(conn.execute(vendors_sql_plain).mappings().all(), 8)
            recent = _rows(conn.execute(recent_sql).mappings().all(), 25)
    except Exception as exc:
        return None, str(exc)
    return {
        "site": site_key.upper(),
        "totals": totals,
        "vendors": vendors,
        "recent_pending": recent,
    }, None


def recent_for_product(bcode: str, *, site: str, limit: int = 15) -> dict[str, Any]:
    code = (bcode or "").strip()
    site_key = (site or "hq").strip().lower()
    out: dict[str, Any] = {"sales": [], "pi": [], "po": [], "iclow": [], "error": None}
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        out["error"] = str(exc)
        return out
    queries = {
        "sales": "SELECT TOP 15 BILLNO, BILLDATE, QTY, UI, PRICE, AMOUNT FROM dbo.SIDET WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY BILLDATE DESC",
        "pi": "SELECT TOP 15 BILLNO, BILLDATE, QTY, UI, PRICE, AMOUNT FROM dbo.PIDET WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY BILLDATE DESC",
        "po": "SELECT TOP 15 DOCNO, DOCDATE, QTY, UI, PRICE, AMOUNT FROM dbo.PODET WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY DOCDATE DESC",
        "iclow": "SELECT TOP 15 DOCNO, DOCDATE, ORDERED, RECEIVED, CANCELED, RCVDNO, QTY, BCODE FROM dbo.ICLOW WHERE LTRIM(RTRIM(BCODE)) = :bcode ORDER BY DOCDATE DESC",
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
