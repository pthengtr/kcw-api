"""Explorer AP tab: vendor search + AI reorder suggest + ICLOW for that vendor."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine
from src.parts9_explorer.insights import _db_path
from src.parts9_explorer.search import _iclow_status, _row


def _snaps_dir() -> Path:
    env = (os.getenv("PRODUCT_INSIGHTS_SNAP_DIR") or "").strip()
    if env:
        return Path(env).expanduser()
    data = (os.getenv("PRODUCT_INSIGHTS_DATA_DIR") or "").strip()
    if data:
        return Path(data).expanduser() / "snaps"
    return Path.home() / "kcw-data" / "product_insights" / "snaps"


def _latest_snap_path() -> Path | None:
    paths = list(_snaps_dir().glob("*/snapshot.sqlite"))
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def classify_order_status(
    *,
    dead_stock: str | None,
    order_ok: str | None,
    company_qtyoh: float | None,
    safe_holding_qty: float | None,
    rec_qtymin: float | None,
    do_not_restock: bool = False,
) -> str:
    """Match Explorer renderInsight / analytic classify_order_status."""
    dead = (dead_stock or "").strip().lower() or None
    ok = (order_ok or "").strip().lower() or None
    if dead == "yes":
        return "dead_stock"
    oh = _f(company_qtyoh)
    hold = _f(safe_holding_qty)
    trigger = _f(rec_qtymin)
    if oh is not None and hold is not None and oh >= hold:
        status = "no_order_needed"
    elif oh is not None and trigger is not None and oh <= trigger:
        status = "should_order"
    elif ok == "caution" or dead == "maybe":
        status = "caution"
    elif ok == "no":
        status = "caution"
    elif oh is not None and hold is not None and oh < hold:
        status = "should_order"
    elif ok == "yes":
        status = "no_order_needed"
    else:
        status = "caution"
    if do_not_restock and status != "dead_stock":
        return "caution"
    return status


def search_ap(q: str, *, site: str = "hq", limit: int = 40) -> tuple[list[dict[str, Any]], str | None]:
    """Search APMAS by acctno / name."""
    qn = (q or "").strip()
    site_key = (site or "hq").strip().lower()
    try:
        engine = get_site_engine("hq")  # APMAS lives on HQ
    except Exception as exc:
        return [], f"APMAS unavailable: {exc}"
    like = f"%{qn}%" if qn else "%"
    lim = max(1, min(int(limit), 100))
    sql = text(
        f"""
        SELECT TOP {lim}
          LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PHONE,'')))) AS PHONE,
          LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(CONTACT,'')))) AS CONTACT,
          LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) AS CANCELED
        FROM dbo.APMAS
        WHERE (
          :empty = 1
          OR LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) LIKE :like
          OR LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) LIKE :like
        )
          AND ISNULL(LTRIM(RTRIM(CONVERT(nvarchar(10), CANCELED))), '') <> 'Y'
        ORDER BY
          CASE WHEN LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :exact THEN 0 ELSE 1 END,
          ACCTNAME
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql,
                {
                    "like": like,
                    "exact": qn,
                    "empty": 0 if qn else 1,
                },
            ).mappings().all()
    except Exception as exc:
        return [], f"APMAS query failed: {exc}"
    out = []
    for r in rows:
        out.append(
            {
                "acctno": (r.get("ACCTNO") or "").strip(),
                "acctname": (r.get("ACCTNAME") or "").strip(),
                "phone": (r.get("PHONE") or "").strip() or None,
                "contact": (r.get("CONTACT") or "").strip() or None,
                "canceled": (r.get("CANCELED") or "").strip().upper() == "Y",
            }
        )
    return out, None


def get_ap_account(acctno: str) -> dict[str, Any] | None:
    code = (acctno or "").strip()
    if not code:
        return None
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                      LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO,
                      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME,
                      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR1,'')))) AS ADDR1,
                      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR2,'')))) AS ADDR2,
                      LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PHONE,'')))) AS PHONE,
                      LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MOBILE,'')))) AS MOBILE,
                      LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(CONTACT,'')))) AS CONTACT,
                      LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(EMAIL,'')))) AS EMAIL
                    FROM dbo.APMAS
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :a
                    """
                ),
                {"a": code},
            ).mappings().first()
    except Exception:
        return {"acctno": code, "acctname": None}
    if not row:
        return {"acctno": code, "acctname": None}
    return {
        "acctno": (row.get("ACCTNO") or code).strip(),
        "acctname": (row.get("ACCTNAME") or "").strip() or None,
        "addr1": (row.get("ADDR1") or "").strip() or None,
        "addr2": (row.get("ADDR2") or "").strip() or None,
        "phone": (row.get("PHONE") or "").strip() or None,
        "mobile": (row.get("MOBILE") or "").strip() or None,
        "contact": (row.get("CONTACT") or "").strip() or None,
        "email": (row.get("EMAIL") or "").strip() or None,
    }


def _skus_from_snap(acctno: str, *, days: int, limit: int) -> tuple[list[dict[str, Any]], str | None, str | None]:
    snap = _latest_snap_path()
    if not snap or not snap.is_file():
        return [], "no snapshot", None
    snap_id = snap.parent.name
    cutoff = (date.today() - timedelta(days=max(1, days))).isoformat()
    conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT d.bcode AS bcode,
                   COALESCE(MAX(i.descr), '') AS descr,
                   SUM(COALESCE(d.qty, 0)) AS buy_qty,
                   COUNT(*) AS buy_lines,
                   MAX(d.billdate) AS last_buy_date,
                   MAX(CASE WHEN d.billdate = mx.mxd THEN d.price END) AS last_buy_price
            FROM pidet d
            JOIN pimas p ON p.src_site = d.src_site AND p.billno = d.billno
            LEFT JOIN icmas i ON i.bcode = d.bcode
            JOIN (
              SELECT d2.bcode AS bcode, MAX(d2.billdate) AS mxd
              FROM pidet d2
              JOIN pimas p2 ON p2.src_site = d2.src_site AND p2.billno = d2.billno
              WHERE LTRIM(RTRIM(COALESCE(p2.acctno, ''))) = ?
                AND COALESCE(d2.billdate, '') >= ?
                AND UPPER(COALESCE(d2.billno, '')) NOT LIKE 'TF%'
                AND UPPER(COALESCE(d2.billno, '')) NOT LIKE '3TF%'
                AND UPPER(COALESCE(d2.billno, '')) NOT LIKE 'TFV%'
                AND UPPER(COALESCE(d2.billno, '')) NOT LIKE 'CNTF%'
              GROUP BY d2.bcode
            ) mx ON mx.bcode = d.bcode
            WHERE LTRIM(RTRIM(COALESCE(p.acctno, ''))) = ?
              AND COALESCE(d.billdate, '') >= ?
              AND UPPER(COALESCE(d.billno, '')) NOT LIKE 'TF%'
              AND UPPER(COALESCE(d.billno, '')) NOT LIKE '3TF%'
              AND UPPER(COALESCE(d.billno, '')) NOT LIKE 'TFV%'
              AND UPPER(COALESCE(d.billno, '')) NOT LIKE 'CNTF%'
            GROUP BY d.bcode
            ORDER BY buy_qty DESC, buy_lines DESC
            LIMIT ?
            """,
            (acctno.strip(), cutoff, acctno.strip(), cutoff, int(limit)),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        bcode = (r["bcode"] or "").strip()
        if not bcode:
            continue
        out.append(
            {
                "bcode": bcode,
                "descr": (r["descr"] or "").strip(),
                "buy_qty": _f(r["buy_qty"]) or 0.0,
                "buy_lines": int(r["buy_lines"] or 0),
                "last_buy_date": (r["last_buy_date"] or "")[:10] or None,
                "last_buy_price": _f(r["last_buy_price"]),
            }
        )
    return out, None, snap_id


def _batch_live_stock(bcodes: list[str], *, site: str) -> dict[str, dict[str, Any]]:
    """Return {bcode: {qtyoh_hq, qtyoh_syp, qtymin_hq, qtymin_syp, do_not_restock, descr, ui1}}."""
    codes = [c.strip() for c in bcodes if c and c.strip()]
    if not codes:
        return {}
    out: dict[str, dict[str, Any]] = {
        c: {
            "qtyoh_hq": None,
            "qtyoh_syp": None,
            "qtymin_hq": None,
            "qtymin_syp": None,
            "do_not_restock": False,
            "descr": None,
            "ui1": None,
        }
        for c in codes
    }

    def _fill(site_key: str, field_oh: str, field_min: str) -> None:
        try:
            engine = get_site_engine(site_key)
        except Exception:
            return
        # chunk IN lists
        for i in range(0, len(codes), 80):
            chunk = codes[i : i + 80]
            params = {f"b{j}": c for j, c in enumerate(chunk)}
            placeholders = ", ".join(f":b{j}" for j in range(len(chunk)))
            sql = text(
                f"""
                SELECT LTRIM(RTRIM(BCODE)) AS BCODE,
                       DESCR, UI1, QTYOH2, QTYMIN
                FROM dbo.ICMAS
                WHERE LTRIM(RTRIM(BCODE)) IN ({placeholders})
                """
            )
            try:
                with engine.connect() as conn:
                    for r in conn.execute(sql, params).mappings().all():
                        b = (r.get("BCODE") or "").strip()
                        if b not in out:
                            continue
                        out[b][field_oh] = _f(r.get("QTYOH2"))
                        out[b][field_min] = _f(r.get("QTYMIN"))
                        qtymin = _f(r.get("QTYMIN"))
                        if site_key == "hq" and qtymin is not None and qtymin < 0:
                            out[b]["do_not_restock"] = True
                        if not out[b]["descr"]:
                            out[b]["descr"] = (str(r.get("DESCR") or "")).strip() or None
                        if not out[b]["ui1"]:
                            out[b]["ui1"] = (str(r.get("UI1") or "")).strip() or None
            except Exception:
                return

    _fill("hq", "qtyoh_hq", "qtymin_hq")
    _fill("syp", "qtyoh_syp", "qtymin_syp")
    return out


def _batch_insights(site: str, bcodes: list[str]) -> dict[str, dict[str, Any]]:
    path = _db_path()
    if not path or not path.is_file() or not bcodes:
        return {}
    site_l = (site or "hq").lower()
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(product_insights)")}
        want = [
            "bcode",
            "generated_at",
            "facts_as_of",
            "summary",
            "order_ok",
            "dead_stock",
            "suggested_order_qty",
            "order_unit",
            "rec_qtymin",
            "safe_holding_qty",
            "last_supplier",
            "last_buy_price",
            "last_buy_date",
            "insight_json",
        ]
        if "last_supplier_acct" in cols:
            want.append("last_supplier_acct")
        select = ", ".join(c for c in want if c == "bcode" or c in cols or c in ("bcode",))
        # ensure bcode always
        select_cols = [c for c in want if c in cols or c == "bcode"]
        select = ", ".join(select_cols)
        for i in range(0, len(bcodes), 200):
            chunk = bcodes[i : i + 200]
            ph = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT {select} FROM product_insights WHERE site = ? AND bcode IN ({ph})",
                [site_l, *chunk],
            ).fetchall()
            for r in rows:
                b = (r["bcode"] or "").strip()
                summary = r["summary"] if "summary" in r.keys() else None
                if not summary and "insight_json" in r.keys():
                    try:
                        j = json.loads(r["insight_json"] or "{}")
                        summary = j.get("ai_action") or j.get("summary")
                    except Exception:
                        pass
                out[b] = {
                    "status": "ready",
                    "generated_at": r["generated_at"] if "generated_at" in r.keys() else None,
                    "facts_as_of": r["facts_as_of"] if "facts_as_of" in r.keys() else None,
                    "summary": summary,
                    "order_ok": r["order_ok"] if "order_ok" in r.keys() else None,
                    "dead_stock": r["dead_stock"] if "dead_stock" in r.keys() else None,
                    "suggested_order_qty": _f(r["suggested_order_qty"]) if "suggested_order_qty" in r.keys() else None,
                    "order_unit": r["order_unit"] if "order_unit" in r.keys() else None,
                    "rec_qtymin": _f(r["rec_qtymin"]) if "rec_qtymin" in r.keys() else None,
                    "safe_holding_qty": _f(r["safe_holding_qty"]) if "safe_holding_qty" in r.keys() else None,
                    "last_supplier": r["last_supplier"] if "last_supplier" in r.keys() else None,
                    "last_buy_price": _f(r["last_buy_price"]) if "last_buy_price" in r.keys() else None,
                    "last_buy_date": r["last_buy_date"] if "last_buy_date" in r.keys() else None,
                }
        # queue status for missing
        missing = [c for c in bcodes if c not in out]
        for i in range(0, len(missing), 200):
            chunk = missing[i : i + 200]
            if not chunk:
                break
            ph = ",".join("?" * len(chunk))
            qrows = conn.execute(
                f"""
                SELECT bcode, status FROM insight_queue
                WHERE site = ? AND bcode IN ({ph})
                  AND status IN ('pending', 'running')
                """,
                [site_l, *chunk],
            ).fetchall()
            for r in qrows:
                b = (r["bcode"] or "").strip()
                if b not in out:
                    out[b] = {"status": "working"}
    finally:
        conn.close()
    return out


def iclow_for_vendor(acctno: str, *, site: str = "hq", limit: int = 300) -> tuple[list[dict[str, Any]], dict[str, int], str | None]:
    code = (acctno or "").strip()
    site_key = (site or "hq").strip().lower()
    counts = {"pending": 0, "received": 0, "canceled": 0, "to_order": 0}
    if not code:
        return [], counts, None
    try:
        engine = get_site_engine(site_key)
    except Exception as exc:
        return [], counts, str(exc)
    lim = max(1, min(int(limit), 500))
    sql = text(
        f"""
        SELECT TOP {lim}
          DOCNO, DOCDATE, VENDOR, BCODE, DESCR, QTY, UI, PRICE, AMOUNT,
          ORDERED, RECEIVED, CANCELED, RCVDDATE, RCVDNO
        FROM dbo.ICLOW
        WHERE LTRIM(RTRIM(COALESCE(VENDOR,''))) = :v
        ORDER BY
          CASE
            WHEN ISNULL(ORDERED,'N') <> 'Y' AND ISNULL(CANCELED,'N') <> 'Y' THEN 0
            WHEN ORDERED = 'Y' AND ISNULL(RECEIVED,'N') = 'N' AND ISNULL(CANCELED,'N') = 'N' THEN 1
            ELSE 2
          END,
          DOCDATE DESC, BCODE
        """
    )
    try:
        with engine.connect() as conn:
            lines = [_row(r) for r in conn.execute(sql, {"v": code}).mappings().all()]
    except Exception as exc:
        return [], counts, str(exc)
    out = []
    for line in lines:
        st = _iclow_status(line)
        counts[st] = counts.get(st, 0) + 1
        bcode = (line.get("BCODE") or "").strip()
        out.append(
            {
                "docno": (line.get("DOCNO") or "").strip(),
                "docdate": (line.get("DOCDATE") or "")[:10],
                "vendor": (line.get("VENDOR") or "").strip(),
                "bcode": bcode,
                "descr": (line.get("DESCR") or "").strip(),
                "qty": _f(line.get("QTY")),
                "ui": (line.get("UI") or "").strip(),
                "amount": _f(line.get("AMOUNT")),
                "status": st,
                "rcvdno": (line.get("RCVDNO") or "").strip() or None,
            }
        )
    return out, counts, None


def ap_detail(
    acctno: str,
    *,
    site: str = "hq",
    days: int = 365,
    sku_limit: int = 250,
) -> dict[str, Any]:
    code = (acctno or "").strip()
    site_l = (site or "hq").strip().lower()
    account = get_ap_account(code) or {"acctno": code, "acctname": None}
    skus, snap_err, snap_id = _skus_from_snap(code, days=days, limit=sku_limit)
    bcodes = [s["bcode"] for s in skus]
    stock = _batch_live_stock(bcodes, site=site_l)
    insights = _batch_insights(site_l, bcodes)
    iclow_lines, iclow_counts, iclow_err = iclow_for_vendor(code, site=site_l)
    iclow_bcodes = {ln["bcode"] for ln in iclow_lines if ln.get("bcode") and ln.get("status") in ("to_order", "pending")}

    ai_lines: list[dict[str, Any]] = []
    counts = {
        "total": 0,
        "should_order": 0,
        "no_order_needed": 0,
        "caution": 0,
        "dead_stock": 0,
        "pending_insight": 0,
        "in_iclow": 0,
    }
    for s in skus:
        b = s["bcode"]
        st = stock.get(b) or {}
        ins = insights.get(b)
        qty_hq = st.get("qtyoh_hq")
        qty_syp = st.get("qtyoh_syp")
        company = None
        if qty_hq is not None or qty_syp is not None:
            company = (qty_hq or 0.0) + (qty_syp or 0.0)
        insight_status = (ins or {}).get("status") if ins else "no_insight"
        if insight_status == "ready":
            order_status = classify_order_status(
                dead_stock=(ins or {}).get("dead_stock"),
                order_ok=(ins or {}).get("order_ok"),
                company_qtyoh=company,
                safe_holding_qty=(ins or {}).get("safe_holding_qty"),
                rec_qtymin=(ins or {}).get("rec_qtymin"),
                do_not_restock=bool(st.get("do_not_restock")),
            )
            suggest_qty = (ins or {}).get("suggested_order_qty") if order_status == "should_order" else None
            if order_status != "should_order":
                suggest_qty = None
            elif suggest_qty is None:
                suggest_qty = (ins or {}).get("suggested_order_qty")
        elif insight_status == "working":
            order_status = "pending_insight"
            suggest_qty = None
        else:
            order_status = "pending_insight"
            suggest_qty = None

        in_iclow = b in iclow_bcodes
        counts["total"] += 1
        if order_status in counts:
            counts[order_status] += 1
        if in_iclow:
            counts["in_iclow"] += 1

        ai_lines.append(
            {
                "bcode": b,
                "descr": s.get("descr") or st.get("descr") or "",
                "buy_qty": s.get("buy_qty"),
                "buy_lines": s.get("buy_lines"),
                "pi_last_buy_date": s.get("last_buy_date"),
                "qtyoh_hq": qty_hq,
                "qtyoh_syp": qty_syp,
                "qtyoh_total": company,
                "rec_qtymin": (ins or {}).get("rec_qtymin") if ins else None,
                "safe_holding_qty": (ins or {}).get("safe_holding_qty") if ins else None,
                "suggested_order_qty": suggest_qty if order_status == "should_order" else (
                    (ins or {}).get("suggested_order_qty") if insight_status == "ready" else None
                ),
                "order_qty_now": suggest_qty,
                "order_unit": (ins or {}).get("order_unit") if ins else st.get("ui1"),
                "order_status": order_status,
                "insight_status": insight_status if insight_status != "ready" else "ready",
                "dead_stock": (ins or {}).get("dead_stock") if ins else None,
                "summary": (ins or {}).get("summary") if ins else None,
                "generated_at": (ins or {}).get("generated_at") if ins else None,
                "in_iclow": in_iclow,
                "do_not_restock": bool(st.get("do_not_restock")),
            }
        )

    # should_order first, then caution, then others; within group by buy_qty desc
    rank = {
        "should_order": 0,
        "caution": 1,
        "pending_insight": 2,
        "no_order_needed": 3,
        "dead_stock": 4,
    }
    ai_lines.sort(key=lambda x: (rank.get(x["order_status"], 9), -(x.get("buy_qty") or 0)))

    overlap = sorted({ln["bcode"] for ln in ai_lines if ln.get("in_iclow") and ln.get("order_status") == "should_order"})

    return {
        "account": account,
        "site": site_l,
        "days": days,
        "snap_id": snap_id,
        "snap_error": snap_err,
        "ai_lines": ai_lines,
        "ai_counts": counts,
        "iclow_lines": iclow_lines,
        "iclow_counts": iclow_counts,
        "iclow_error": iclow_err,
        "overlap_bcodes": overlap,
    }
