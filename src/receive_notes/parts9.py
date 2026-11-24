from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import format_sql_error, get_site_engine

_BKK = ZoneInfo("Asia/Bangkok")

_BILL_COLS = (
    "BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, PAID, NOTENO, VOUCNO2, "
    "BILLTYPE, CANCELED, REMARKS, DUEDATE, CASHED, JOURMODE, PAYSTAT"
)


def _site_key(site: str) -> str:
    return (site or "hq").strip().lower()


def _iso_date(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


def _to_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _format_bill_rows(rows) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["BILLDATE"] = _iso_date(item.get("BILLDATE"))
        item["DUEDATE"] = _iso_date(item.get("DUEDATE"))
        if "AFTERTAX" in item:
            item["AFTERTAX"] = _to_float(item.get("AFTERTAX"))
        out.append(item)
    return out


def search_debtors(site: str, q: str, *, limit: int = 30) -> list[dict[str, Any]]:
    needle = (q or "").strip()
    if len(needle) < 1:
        return []
    eng = get_site_engine(_site_key(site))
    pat = f"%{needle}%"
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          LTRIM(RTRIM(COALESCE(MOBILE, ''))) AS tax_id
        FROM dbo.ARMAS
        WHERE ISNULL(CANCELED, 'N') <> 'Y'
          AND (
            LTRIM(RTRIM(ACCTNO)) LIKE :pat
            OR LTRIM(RTRIM(ACCTNAME)) LIKE :pat
            OR LTRIM(RTRIM(COALESCE(MOBILE, ''))) LIKE :pat
          )
        ORDER BY ACCTNAME
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, {"pat": pat, "lim": limit}).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    return [dict(r) for r in rows]


def get_debtor(site: str, acctno: str) -> dict[str, Any] | None:
    """ARMAS row for printable bill header (address + tax id)."""
    acct = (acctno or "").strip()
    if not acct:
        return None
    eng = get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP 1
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          LTRIM(RTRIM(COALESCE(ADDR1, ''))) AS addr1,
          LTRIM(RTRIM(COALESCE(ADDR2, ''))) AS addr2,
          LTRIM(RTRIM(COALESCE(MOBILE, ''))) AS tax_id
        FROM dbo.ARMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        """
    )
    try:
        with eng.connect() as conn:
            row = conn.execute(sql, {"acctno": acct}).mappings().first()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    if not row:
        return None
    item = dict(row)
    parts = [str(item.get("addr1") or "").strip(), str(item.get("addr2") or "").strip()]
    item["address"] = "\n".join(p for p in parts if p)
    return item


def list_pickable_bills(
    site: str,
    acctno: str,
    *,
    limit: int = 200,
    include_noted: bool = True,
) -> list[dict[str, Any]]:
    """Open credit bills (CASHED=N, unpaid, unvouchered)."""
    acct = (acctno or "").strip()
    if not acct:
        return []
    eng = get_site_engine(_site_key(site))
    note_clause = ""
    if not include_noted:
        note_clause = "AND ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''"
    sql = text(
        f"""
        SELECT TOP (:lim) {_BILL_COLS}
        FROM dbo.SIMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND ISNULL(CASHED, 'Y') = 'N'
          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
          AND ISNULL(PAID, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
          AND JOURMODE IN ('1', '2')
          {note_clause}
        ORDER BY BILLDATE DESC, BILLNO DESC
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, {"acctno": acct, "lim": limit}).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    return _format_bill_rows(rows)


def fetch_bills_for_receive(
    site: str,
    acctno: str,
    billnos: list[str],
    *,
    engine: Engine | None = None,
    noteno: str | None = None,
) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    nums = [b.strip() for b in billnos if (b or "").strip()]
    if not acct or not nums:
        return []
    eng = engine or get_site_engine(_site_key(site))
    placeholders = ", ".join(f":b{i}" for i in range(len(nums)))
    params: dict[str, Any] = {"acctno": acct}
    for i, b in enumerate(nums):
        params[f"b{i}"] = b
    if note:
        params["noteno"] = note
        noteno_clause = (
            "AND (ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''"
            " OR LTRIM(RTRIM(NOTENO)) = :noteno)"
        )
    else:
        noteno_clause = ""
    sql = text(
        f"""
        SELECT {_BILL_COLS}
        FROM dbo.SIMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(BILLNO)) IN ({placeholders})
          {noteno_clause}
          AND ISNULL(CASHED, 'Y') = 'N'
          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
          AND ISNULL(PAID, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
          AND JOURMODE IN ('1', '2')
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()
    return _format_bill_rows(rows)


def list_note_bills(
    site: str,
    acctno: str,
    noteno: str,
    *,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return []
    eng = engine or get_site_engine(_site_key(site))
    sql = text(
        f"""
        SELECT {_BILL_COLS}
        FROM dbo.SIMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(NOTENO)) = :noteno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        ORDER BY BILLDATE DESC, BILLNO DESC
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql, {"acctno": acct, "noteno": note}).mappings().all()
    return _format_bill_rows(rows)


def get_note_header(
    site: str,
    acctno: str,
    noteno: str,
    *,
    engine: Engine | None = None,
    include_canceled: bool = False,
) -> dict[str, Any] | None:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return None
    eng = engine or get_site_engine(_site_key(site))
    cancel_clause = "" if include_canceled else "AND ISNULL(CANCELED, 'N') <> 'Y'"
    sql = text(
        f"""
        SELECT TOP 1
          ID, JOURMODE, JOURTYPE, NOTED, NOTEDATE,
          LTRIM(RTRIM(NOTENO)) AS noteno,
          VOUCED, VOUCDATE,
          LTRIM(RTRIM(COALESCE(VOUCNO, ''))) AS voucno,
          RCPTNO,
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          BILLCNT, BILLAMT, DISCOUNT, NETAMT, PAYAMT,
          CHKAMT, CASHAMT, PAID, CANCELED, POSTED1, POSTED2, DONE
        FROM dbo.RVMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(NOTENO)) = :noteno
          {cancel_clause}
        ORDER BY NOTEDATE DESC
        """
    )
    with eng.connect() as conn:
        row = conn.execute(sql, {"acctno": acct, "noteno": note}).mappings().first()
    if not row:
        return None
    item = dict(row)
    item["NOTEDATE"] = _iso_date(item.get("NOTEDATE"))
    item["VOUCDATE"] = _iso_date(item.get("VOUCDATE"))
    item["canceled"] = str(item.get("CANCELED") or "N").strip().upper() == "Y"
    for key in ("BILLAMT", "DISCOUNT", "NETAMT", "PAYAMT", "CHKAMT", "CASHAMT"):
        if key in item:
            item[key] = _to_float(item.get(key)) if item.get(key) is not None else None
    return item


def get_voucher_header(
    site: str,
    voucno: str,
    *,
    engine: Engine | None = None,
) -> dict[str, Any] | None:
    vno = (voucno or "").strip()
    if not vno:
        return None
    eng = engine or get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP 1
          ID, JOURMODE, JOURTYPE, NOTED, NOTEDATE, NOTENO,
          VOUCED, VOUCDATE, VOUCNO, RCPTNO,
          ACCTNO, ACCTNAME, BILLCNT, BILLAMT, DISCOUNT, NETAMT, PAYAMT,
          CHKAMT, CASHAMT, PAID, CANCELED, POSTED1, POSTED2, DONE
        FROM dbo.RVMAS
        WHERE LTRIM(RTRIM(VOUCNO)) = :voucno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        """
    )
    with eng.connect() as conn:
        row = conn.execute(sql, {"voucno": vno}).mappings().first()
    if not row:
        return None
    item = dict(row)
    item["NOTEDATE"] = _iso_date(item.get("NOTEDATE"))
    item["VOUCDATE"] = _iso_date(item.get("VOUCDATE"))
    return item


def list_pending_notes_raw(site: str, *, limit: int = 200) -> list[dict[str, Any]]:
    """Unvouchered RVMAS notes (no overlay merge)."""
    eng = get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          LTRIM(RTRIM(NOTENO)) AS noteno,
          NOTEDATE, JOURMODE, BILLCNT, BILLAMT
        FROM dbo.RVMAS
        WHERE NOTED = 'Y'
          AND ISNULL(VOUCED, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
        ORDER BY NOTEDATE DESC, NOTENO DESC
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, {"lim": limit}).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    out = []
    for row in rows:
        item = dict(row)
        item["NOTEDATE"] = _iso_date(item.get("NOTEDATE"))
        item["BILLAMT"] = _to_float(item.get("BILLAMT"))
        out.append(item)
    return out


def list_pending_notes(site: str, overlays: list[dict[str, Any]] | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
    """Inner join KSS RVMAS with receive_note.note overlay rows (AP-style).

    When overlays is None, returns raw KSS pending (legacy).
    """
    if overlays is None:
        return list_pending_notes_raw(site, limit=limit)
    if not overlays:
        return []
    eng = get_site_engine(_site_key(site))
    keys = [
        (r["acctno"].strip(), r["noteno"].strip())
        for r in overlays
        if r.get("acctno") and r.get("noteno") and str(r.get("status") or "open") == "open"
    ]
    if not keys:
        return []
    clauses = []
    params: dict[str, Any] = {}
    for i, (acct, note) in enumerate(keys):
        clauses.append(f"(LTRIM(RTRIM(ACCTNO)) = :a{i} AND LTRIM(RTRIM(NOTENO)) = :n{i})")
        params[f"a{i}"] = acct
        params[f"n{i}"] = note
    where = " OR ".join(clauses)
    sql = text(
        f"""
        SELECT LTRIM(RTRIM(ACCTNO)) AS acctno,
               LTRIM(RTRIM(ACCTNAME)) AS acctname,
               LTRIM(RTRIM(NOTENO)) AS noteno,
               NOTEDATE, BILLCNT, BILLAMT, VOUCED, VOUCNO, JOURMODE
        FROM dbo.RVMAS
        WHERE NOTED = 'Y'
          AND ISNULL(VOUCED, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
          AND ({where})
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    by_key = {(r["acctno"], r["noteno"]): dict(r) for r in rows}
    out: list[dict[str, Any]] = []
    for rem in overlays:
        if str(rem.get("status") or "open") != "open":
            continue
        acct = rem.get("acctno", "").strip()
        note = rem.get("noteno", "").strip()
        rvmas = by_key.get((acct, note))
        if not rvmas:
            continue
        merged = {**rvmas, "reminder": rem}
        method = (rem.get("settle_method") or "").strip().lower()
        merged["settle_method"] = method if method in ("transfer", "cheque", "cash") else "transfer"
        nd = rvmas.get("NOTEDATE")
        if isinstance(nd, datetime):
            merged["NOTEDATE"] = nd.date().isoformat()
        elif isinstance(nd, date):
            merged["NOTEDATE"] = nd.isoformat()
        merged["BILLAMT"] = _to_float(merged.get("BILLAMT"))
        out.append(merged)
    out.sort(key=lambda x: (x.get("reminder") or {}).get("due_date") or "")
    return out[:limit]


def list_canceled_notes(site: str, overlays: list[dict[str, Any]], *, limit: int = 200) -> list[dict[str, Any]]:
    """Canceled billing notes (overlay status=canceled) joined to KSS RVMAS including CANCELED='Y'."""
    if not overlays:
        return []
    eng = get_site_engine(_site_key(site))
    keys = [
        (r["acctno"].strip(), r["noteno"].strip())
        for r in overlays
        if r.get("acctno")
        and r.get("noteno")
        and str(r.get("status") or "").strip().lower() == "canceled"
    ]
    if not keys:
        return []
    clauses = []
    params: dict[str, Any] = {}
    for i, (acct, note) in enumerate(keys):
        clauses.append(f"(LTRIM(RTRIM(ACCTNO)) = :a{i} AND LTRIM(RTRIM(NOTENO)) = :n{i})")
        params[f"a{i}"] = acct
        params[f"n{i}"] = note
    where = " OR ".join(clauses)
    sql = text(
        f"""
        SELECT LTRIM(RTRIM(ACCTNO)) AS acctno,
               LTRIM(RTRIM(ACCTNAME)) AS acctname,
               LTRIM(RTRIM(NOTENO)) AS noteno,
               NOTEDATE, BILLCNT, BILLAMT, VOUCED, VOUCNO, JOURMODE, CANCELED
        FROM dbo.RVMAS
        WHERE NOTED = 'Y'
          AND ({where})
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    by_key = {(r["acctno"], r["noteno"]): dict(r) for r in rows}
    out: list[dict[str, Any]] = []
    for rem in overlays:
        if str(rem.get("status") or "").strip().lower() != "canceled":
            continue
        acct = rem.get("acctno", "").strip()
        note = rem.get("noteno", "").strip()
        rvmas = by_key.get((acct, note)) or {
            "acctno": acct,
            "acctname": "",
            "noteno": note,
            "NOTEDATE": rem.get("created_at"),
            "BILLCNT": 0,
            "BILLAMT": 0,
            "VOUCED": "N",
            "VOUCNO": "",
            "CANCELED": "Y",
        }
        merged = {**rvmas, "reminder": rem, "canceled": True, "settle_method": rem.get("settle_method")}
        nd = merged.get("NOTEDATE")
        if isinstance(nd, datetime):
            merged["NOTEDATE"] = nd.date().isoformat()
        elif isinstance(nd, date):
            merged["NOTEDATE"] = nd.isoformat()
        merged["BILLAMT"] = _to_float(merged.get("BILLAMT"))
        out.append(merged)
    out.sort(key=lambda x: (x.get("reminder") or {}).get("due_date") or x.get("NOTEDATE") or "", reverse=True)
    return out[:limit]


def list_vouchered(
    site: str,
    *,
    limit: int = 200,
    days: int = 60,
) -> list[dict[str, Any]]:
    eng = get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          LTRIM(RTRIM(COALESCE(NOTENO, ''))) AS noteno,
          LTRIM(RTRIM(VOUCNO)) AS voucno,
          VOUCDATE, JOURMODE, BILLCNT, BILLAMT, DISCOUNT, NETAMT, PAYAMT, CHKAMT, CASHAMT
        FROM dbo.RVMAS
        WHERE VOUCED = 'Y'
          AND ISNULL(CANCELED, 'N') <> 'Y'
          AND VOUCDATE >= DATEADD(day, -:days, CAST(GETDATE() AS date))
        ORDER BY VOUCDATE DESC, VOUCNO DESC
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, {"lim": limit, "days": days}).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    out = []
    for row in rows:
        item = dict(row)
        item["VOUCDATE"] = _iso_date(item.get("VOUCDATE"))
        for key in ("BILLAMT", "DISCOUNT", "NETAMT", "PAYAMT", "CHKAMT", "CASHAMT"):
            item[key] = _to_float(item.get(key)) if item.get(key) is not None else None
        out.append(item)
    return out


def infer_settle_method(
    chkno: str | None,
    *,
    bankname: str | None = None,
    acctno: str | None = None,
) -> str:
    """Infer actual receive channel from BRDET (prefer bank/GL over CHKNO text)."""
    bank = (bankname or "").strip()
    gl = (acctno or "").strip()
    text_v = (chkno or "").strip()
    if not bank and not gl:
        return "cash"
    if gl or text_v == "โอน":
        return "transfer"
    return "cheque"


def _overlay_settle_method(rem: dict[str, Any] | None) -> str:
    method = str((rem or {}).get("settle_method") or "").strip().lower()
    return method if method in ("transfer", "cheque", "cash") else ""


def _brdet_settle_map(eng: Engine, voucnums: list[str]) -> dict[str, str] | None:
    """Map VOUCNO → actual settle_method from first active BRDET line.

    Returns None when the BRDET query itself fails (caller may fall back to overlay).
    """
    nums = sorted({(v or "").strip() for v in voucnums if (v or "").strip()})
    if not nums:
        return {}
    placeholders = ", ".join(f":v{i}" for i in range(len(nums)))
    params = {f"v{i}": n for i, n in enumerate(nums)}
    sql = text(
        f"""
        SELECT LTRIM(RTRIM(VOUCNO)) AS voucno,
               LTRIM(RTRIM(COALESCE(CHKNO, ''))) AS chkno,
               LTRIM(RTRIM(COALESCE(BANKNAME, ''))) AS bankname,
               LTRIM(RTRIM(COALESCE(ACCTNO, ''))) AS acctno
        FROM dbo.BRDET
        WHERE LTRIM(RTRIM(VOUCNO)) IN ({placeholders})
          AND ISNULL(CANCELED, 'N') <> 'Y'
        ORDER BY VOUCNO, CHKDATE, ID
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception:
        return None
    out: dict[str, str] = {}
    for row in rows:
        vo = str(row.get("voucno") or "").strip()
        if not vo or vo in out:
            continue
        out[vo] = infer_settle_method(
            row.get("chkno"),
            bankname=row.get("bankname"),
            acctno=row.get("acctno"),
        )
    return out


def list_vouchered_notes(site: str, overlays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Notes from this service that are vouchered in KSS (for proof queue)."""
    if not overlays:
        return []
    eng = get_site_engine(_site_key(site))
    keys = [
        (r["acctno"].strip(), r["noteno"].strip())
        for r in overlays
        if r.get("acctno") and r.get("noteno")
    ]
    if not keys:
        return []
    clauses = []
    params: dict[str, Any] = {}
    for i, (acct, note) in enumerate(keys):
        clauses.append(f"(LTRIM(RTRIM(ACCTNO)) = :a{i} AND LTRIM(RTRIM(NOTENO)) = :n{i})")
        params[f"a{i}"] = acct
        params[f"n{i}"] = note
    where = " OR ".join(clauses)
    sql = text(
        f"""
        SELECT LTRIM(RTRIM(ACCTNO)) AS acctno,
               LTRIM(RTRIM(ACCTNAME)) AS acctname,
               LTRIM(RTRIM(NOTENO)) AS noteno,
               LTRIM(RTRIM(VOUCNO)) AS voucno,
               VOUCDATE, BILLAMT, NETAMT, PAYAMT, CHKAMT, DISCOUNT, JOURMODE
        FROM dbo.RVMAS
        WHERE VOUCED = 'Y'
          AND ISNULL(CANCELED, 'N') <> 'Y'
          AND ({where})
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    by_key = {(r["acctno"], r["noteno"]): dict(r) for r in rows}
    out: list[dict[str, Any]] = []
    for rem in overlays:
        acct = rem.get("acctno", "").strip()
        note = rem.get("noteno", "").strip()
        rvmas = by_key.get((acct, note))
        if not rvmas:
            continue
        item = {**rvmas, "reminder": rem}
        item["VOUCDATE"] = _iso_date(item.get("VOUCDATE"))
        for key in ("BILLAMT", "DISCOUNT", "NETAMT", "PAYAMT", "CHKAMT"):
            item[key] = _to_float(item.get(key)) if item.get(key) is not None else None
        # Prefer overlay snapshot from รับชำระ; BRDET overrides below when present.
        overlay_method = _overlay_settle_method(rem)
        if overlay_method:
            item["settle_method"] = overlay_method
        out.append(item)
    settle_map = _brdet_settle_map(eng, [str(r.get("voucno") or "") for r in out])
    if settle_map is not None:
        for row in out:
            vo = str(row.get("voucno") or "").strip()
            method = settle_map.get(vo)
            if method:
                row["settle_method"] = method
    return out


def list_bills_for_edit(site: str, acctno: str, noteno: str) -> list[dict[str, Any]]:
    """Attached bills (attached=true) plus pickable unnoted bills for edit UI."""
    attached = list_note_bills(site, acctno, noteno)
    attached_nos = {str(b.get("BILLNO") or "").strip() for b in attached}
    pickable = list_pickable_bills(site, acctno, include_noted=False, limit=200)
    out: list[dict[str, Any]] = []
    for bill in attached:
        item = dict(bill)
        item["attached"] = True
        out.append(item)
    for bill in pickable:
        bno = str(bill.get("BILLNO") or "").strip()
        if bno in attached_nos:
            continue
        item = dict(bill)
        item["attached"] = False
        out.append(item)
    return out


def list_brdet(site: str, voucno: str) -> list[dict[str, Any]]:
    vno = (voucno or "").strip()
    if not vno:
        return []
    eng = get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT ID, VOUCNO, VOUCDATE, CHKNO, CHKDATE, CHKAMT, BANKNAME, ACCTNO,
               PAYTYPE, JOURTYPE, STATUS, DONE, CANCELED
        FROM dbo.BRDET
        WHERE LTRIM(RTRIM(VOUCNO)) = :voucno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        ORDER BY CHKDATE, ID
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql, {"voucno": vno}).mappings().all()
    out = []
    for row in rows:
        item = dict(row)
        item["VOUCDATE"] = _iso_date(item.get("VOUCDATE"))
        item["CHKDATE"] = _iso_date(item.get("CHKDATE"))
        item["CHKAMT"] = _to_float(item.get("CHKAMT")) if item.get("CHKAMT") is not None else None
        out.append(item)
    return out


def assess_receive_edit_gate(
    *,
    header: dict[str, Any] | None,
    payments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect bank-reconciled / period-closed vouchers that need accounting review before edit."""
    reasons: list[str] = []
    hdr = header or {}
    if str(hdr.get("POSTED1") or "N").strip().upper() == "Y":
        reasons.append("period_closed")
    elif str(hdr.get("POSTED2") or "N").strip().upper() == "Y":
        reasons.append("period_closed")
    elif str(hdr.get("DONE") or "N").strip().upper() == "Y":
        reasons.append("period_closed")

    for pay in payments or []:
        if str(pay.get("DONE") or "N").strip().upper() == "Y":
            if "bank_reconciled" not in reasons:
                reasons.append("bank_reconciled")
            break

    # De-dupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        ordered.append(reason)
    return {
        "needs_accounting_review": bool(ordered),
        "reasons": ordered,
    }


def debtor_summary(site: str, acctno: str) -> dict[str, Any]:
    acct = (acctno or "").strip()
    bills = list_pickable_bills(site, acct, limit=500)
    open_amt = sum(_to_float(b.get("AFTERTAX")) for b in bills)
    notes = [
        n
        for n in list_pending_notes_raw(site, limit=500)
        if str(n.get("acctno") or "").strip() == acct
    ]
    vouchers = [
        v
        for v in list_vouchered(site, limit=500, days=365)
        if str(v.get("acctno") or "").strip() == acct
    ]
    return {
        "acctno": acct,
        "open_bill_count": len(bills),
        "open_bill_amount": round(open_amt, 2),
        "open_bills": bills,
        "pending_notes": notes,
        "recent_receipts": vouchers[:50],
    }
