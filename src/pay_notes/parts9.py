from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import format_sql_error, get_site_engine

_BKK = ZoneInfo("Asia/Bangkok")

_BILL_COLS = (
    "BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, PAID, NOTENO, VOUCNO2, BILLTYPE, CANCELED, REMARKS"
)


def _site_key(site: str) -> str:
    return (site or "hq").strip().lower()


def search_vendors(site: str, q: str, *, limit: int = 30) -> list[dict[str, Any]]:
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
        FROM dbo.APMAS
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


def list_pickable_bills(site: str, acctno: str, *, limit: int = 200) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    if not acct:
        return []
    eng = get_site_engine(_site_key(site))
    sql = text(
        f"""
        SELECT TOP (:lim) {_BILL_COLS}
        FROM dbo.PIMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''
          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
          AND ISNULL(PAID, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
        ORDER BY BILLDATE ASC
        """
    )
    try:
        with eng.connect() as conn:
            rows = conn.execute(sql, {"acctno": acct, "lim": limit}).mappings().all()
    except Exception as exc:
        raise RuntimeError(format_sql_error(exc, site=site)) from exc
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        bd = item.get("BILLDATE")
        if isinstance(bd, datetime):
            item["BILLDATE"] = bd.date().isoformat()
        elif isinstance(bd, date):
            item["BILLDATE"] = bd.isoformat()
        out.append(item)
    return out


def fetch_bills_for_note(
    site: str,
    acctno: str,
    billnos: list[str],
    *,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    nums = [b.strip() for b in billnos if (b or "").strip()]
    if not acct or not nums:
        return []
    eng = engine or get_site_engine(_site_key(site))
    placeholders = ", ".join(f":b{i}" for i in range(len(nums)))
    params: dict[str, Any] = {"acctno": acct}
    for i, b in enumerate(nums):
        params[f"b{i}"] = b
    sql = text(
        f"""
        SELECT {_BILL_COLS}, JOURMODE
        FROM dbo.PIMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(BILLNO)) IN ({placeholders})
          AND ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''
          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
          AND ISNULL(PAID, 'N') = 'N'
          AND ISNULL(CANCELED, 'N') <> 'Y'
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]


def note_exists(site: str, acctno: str, noteno: str, *, engine: Engine | None = None) -> bool:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return False
    eng = engine or get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP 1 1 AS ok FROM dbo.PVMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(NOTENO)) = :noteno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        """
    )
    with eng.connect() as conn:
        row = conn.execute(sql, {"acctno": acct, "noteno": note}).first()
    return row is not None


def list_pending_notes(site: str, reminders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inner join KSS PVMAS with pay_note.reminder rows."""
    if not reminders:
        return []
    eng = get_site_engine(_site_key(site))
    keys = [(r["acctno"].strip(), r["noteno"].strip()) for r in reminders if r.get("acctno") and r.get("noteno")]
    if not keys:
        return []
    # Build OR clauses — bounded by reminder count on board
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
               NOTEDATE, BILLCNT, BILLAMT, VOUCED, VOUCNO
        FROM dbo.PVMAS
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
    for rem in reminders:
        acct = rem.get("acctno", "").strip()
        note = rem.get("noteno", "").strip()
        pvmas = by_key.get((acct, note))
        if not pvmas:
            continue
        merged = {**pvmas, "reminder": rem}
        nd = pvmas.get("NOTEDATE")
        if isinstance(nd, datetime):
            merged["NOTEDATE"] = nd.date().isoformat()
        out.append(merged)
    out.sort(key=lambda x: (x.get("reminder") or {}).get("due_date") or "")
    return out


def infer_settle_method(chkno: str | None) -> str:
    """Map BPDET.CHKNO to transfer | cheque | cash for the voucher board."""
    text = (chkno or "").strip()
    if not text:
        return "cash"
    if text == "โอน":
        return "transfer"
    return "cheque"


def _bpdet_chkno_map(eng: Engine, voucnums: list[str]) -> dict[str, str] | None:
    nums = [v.strip() for v in voucnums if (v or "").strip()]
    if not nums:
        return {}
    placeholders = ", ".join(f":v{i}" for i in range(len(nums)))
    params = {f"v{i}": n for i, n in enumerate(nums)}
    sql = text(
        f"""
        SELECT LTRIM(RTRIM(VOUCNO)) AS voucno,
               LTRIM(RTRIM(COALESCE(CHKNO, ''))) AS chkno
        FROM dbo.BPDET
        WHERE LTRIM(RTRIM(VOUCNO)) IN ({placeholders})
          AND ISNULL(CANCELED, 'N') <> 'Y'
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
        if vo and vo not in out:
            out[vo] = str(row.get("chkno") or "")
    return out


def bangkok_today() -> date:
    return datetime.now(_BKK).date()


def get_note_header(site: str, acctno: str, noteno: str) -> dict[str, Any] | None:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return None
    eng = get_site_engine(_site_key(site))
    sql = text(
        """
        SELECT TOP 1
          LTRIM(RTRIM(ACCTNO)) AS acctno,
          LTRIM(RTRIM(ACCTNAME)) AS acctname,
          LTRIM(RTRIM(NOTENO)) AS noteno,
          NOTEDATE, BILLCNT, BILLAMT, DISCOUNT, NETAMT,
          LTRIM(RTRIM(COALESCE(VOUCNO, ''))) AS voucno,
          VOUCDATE, VOUCED, JOURMODE, PAID, CHKAMT
        FROM dbo.PVMAS
        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
          AND LTRIM(RTRIM(NOTENO)) = :noteno
          AND ISNULL(CANCELED, 'N') <> 'Y'
        """
    )
    with eng.connect() as conn:
        row = conn.execute(sql, {"acctno": acct, "noteno": note}).mappings().first()
    if not row:
        return None
    out = dict(row)
    for key in ("NOTEDATE", "VOUCDATE"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.date().isoformat()
        elif isinstance(val, date):
            out[key] = val.isoformat()
    return out


def list_vouchered_notes(site: str, reminders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Notes from this service that are vouchered in KSS (for proof queue)."""
    if not reminders:
        return []
    eng = get_site_engine(_site_key(site))
    keys = [
        (r["acctno"].strip(), r["noteno"].strip())
        for r in reminders
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
               VOUCDATE, BILLAMT, NETAMT, PAYAMT, CHKAMT
        FROM dbo.PVMAS
        WHERE VOUCED = 'Y'
          AND ISNULL(LTRIM(RTRIM(VOUCNO)), '') <> ''
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
    for rem in reminders:
        acct = rem.get("acctno", "").strip()
        note = rem.get("noteno", "").strip()
        pvmas = by_key.get((acct, note))
        if not pvmas:
            continue
        merged = {**pvmas, "reminder": rem}
        vd = pvmas.get("VOUCDATE")
        if isinstance(vd, datetime):
            merged["VOUCDATE"] = vd.date().isoformat()
        elif isinstance(vd, date):
            merged["VOUCDATE"] = vd.isoformat()
        out.append(merged)
    out.sort(key=lambda x: x.get("VOUCDATE") or "")
    chk_map = _bpdet_chkno_map(eng, [str(r.get("voucno") or "") for r in out])
    if chk_map is not None:
        for row in out:
            chkno = chk_map.get(str(row.get("voucno") or "").strip(), "")
            row["chkno"] = chkno
            row["settle_method"] = infer_settle_method(chkno)
    return out
