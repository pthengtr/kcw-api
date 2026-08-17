"""Live customer / product rank and stock-more movement from PARTS9."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text

from src.ops.bi_filters import _num, resolve_range
from src.ops.bi_sales import fetch_revenue_bills
from src.parts9_explorer.db import get_site_engine

_LINE_SQL = text(
    """
    SELECT
      LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) AS BILLNO,
      LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
      MAX(LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DETAIL,''))))) AS DETAIL,
      SUM(
        CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), QTY), ',', '')) = 1
             THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), QTY), ',', ''))
             ELSE 0 END
        * CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', '')) = 1
                AND CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', '')) <> 0
               THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', ''))
               ELSE 1 END
      ) AS QTY,
      SUM(
        CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), AMOUNT), ',', '')) = 1
             THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), AMOUNT), ',', ''))
             ELSE 0 END
      ) AS AMOUNT,
      COUNT(*) AS LINES
    FROM dbo.SIDET
    WHERE CONVERT(varchar(10), BILLDATE, 23) >= :dfrom
      AND CONVERT(varchar(10), BILLDATE, 23) <= :dto
      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
      AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))), '') IS NOT NULL
    GROUP BY LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))),
             LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE)))
    """
)

_BUY_SQL = text(
    """
    SELECT
      LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
      MAX(LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DETAIL,''))))) AS DETAIL,
      SUM(
        CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), QTY), ',', '')) = 1
             THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), QTY), ',', ''))
             ELSE 0 END
        * CASE WHEN ISNUMERIC(REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', '')) = 1
                AND CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', '')) <> 0
               THEN CONVERT(decimal(18,4), REPLACE(CONVERT(varchar(40), COALESCE(MTP,1)), ',', ''))
               ELSE 1 END
      ) AS QTY,
      COUNT(DISTINCT LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO)))) AS BILLS
    FROM dbo.PIDET
    WHERE CONVERT(varchar(10), BILLDATE, 23) >= :dfrom
      AND CONVERT(varchar(10), BILLDATE, 23) <= :dto
      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(JOURMODE,'')))) IN ('1', '2')
      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLTYPE,'')))) IN ('1', '2', '3')
      AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))), '') IS NOT NULL
    GROUP BY LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE)))
    """
)


def _bills_index(start: date, end: date, branch: str | None) -> dict[str, dict[str, Any]]:
    idx = {}
    for b in fetch_revenue_bills(start, end):
        if branch and b["branch"] != branch:
            continue
        idx[b["billno"].upper()] = b
    return idx


def _sidet_lines(start: date, end: date) -> list[dict[str, Any]]:
    params = {"dfrom": start.isoformat(), "dto": end.isoformat()}
    out: list[dict[str, Any]] = []
    for site in ("hq", "syp"):
        engine = get_site_engine(site)
        with engine.connect() as conn:
            rows = conn.execute(_LINE_SQL, params).mappings().all()
        for r in rows:
            out.append(
                {
                    "site": site,
                    "billno": str(r.get("BILLNO") or "").strip(),
                    "bcode": str(r.get("BCODE") or "").strip(),
                    "detail": str(r.get("DETAIL") or "").strip(),
                    "qty": _num(r.get("QTY")),
                    "amount": _num(r.get("AMOUNT")),
                    "lines": int(r.get("LINES") or 0),
                }
            )
    return out


def _icmas_on_hand(bcodes: list[str]) -> dict[str, float]:
    codes = [c for c in bcodes if c]
    if not codes:
        return {}
    out: dict[str, float] = {}
    for site in ("hq", "syp"):
        placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
        params = {f"c{i}": c for i, c in enumerate(codes)}
        sql = text(
            f"SELECT LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE, QTYOH2 "
            f"FROM dbo.ICMAS WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})"
        )
        try:
            engine = get_site_engine(site)
            with engine.connect() as conn:
                for r in conn.execute(sql, params).mappings().all():
                    code = str(r.get("BCODE") or "").strip()
                    if site == "hq" or code not in out:
                        out[code] = _num(r.get("QTYOH2"))
        except Exception:
            continue
    return out


def customer_overview(*, dfrom: str | None, dto: str | None, branch: str | None, limit: int = 50) -> dict[str, Any]:
    start, end = resolve_range(dfrom, dto)
    br = (branch or "").strip().upper() or None
    if br == "ALL":
        br = None
    lim = max(1, min(int(limit or 50), 200))
    bills = [b for b in fetch_revenue_bills(start, end) if br is None or b["branch"] == br]
    ranked: dict[str, dict[str, Any]] = {}
    walkin_rev = 0.0
    walkin_n = 0
    by_branch: dict[str, dict[str, float | int]] = defaultdict(lambda: {"revenue_net": 0.0, "bill_count": 0})
    for b in bills:
        by_branch[b["branch"]]["revenue_net"] += b["revenue_net"]
        by_branch[b["branch"]]["bill_count"] += 1
        acct = b["acctno"]
        if not acct:
            walkin_rev += b["revenue_net"]
            walkin_n += 1
            continue
        row = ranked.setdefault(
            acct,
            {
                "acctno": acct,
                "customer_name": b["acctname"] or "",
                "name_source": "armas" if b["acctname"] else "none",
                "bill_acctname": b["acctname"] or None,
                "in_party": False,
                "in_armas": bool(b["acctname"]),
                "party_kind": None,
                "revenue_net": 0.0,
                "bill_count": 0,
                "avg_bill": 0.0,
                "hq_revenue_net": 0.0,
                "syp_revenue_net": 0.0,
                "online_revenue_net": 0.0,
            },
        )
        if b["acctname"] and not row["customer_name"]:
            row["customer_name"] = b["acctname"]
        row["revenue_net"] += b["revenue_net"]
        row["bill_count"] += 1
        row[{"HQ": "hq_revenue_net", "SYP": "syp_revenue_net", "ONLINE": "online_revenue_net"}[b["branch"]]] += b[
            "revenue_net"
        ]
    for row in ranked.values():
        row["avg_bill"] = row["revenue_net"] / row["bill_count"] if row["bill_count"] else 0.0
    top = sorted(ranked.values(), key=lambda r: -r["revenue_net"])[:lim]
    revenue = sum(b["revenue_net"] for b in bills)
    named = [b for b in bills if b["acctno"]]
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "branch": br,
        "limit": lim,
        "summary": {
            "revenue_net": revenue,
            "customer_count": len(ranked),
            "bill_count": len(bills),
            "avg_bill": (revenue / len(bills)) if bills else 0.0,
            "matched_customer_count": sum(1 for r in ranked.values() if r["customer_name"]),
            "unmatched_customer_count": sum(1 for r in ranked.values() if not r["customer_name"]),
        },
        "walkin_summary": {"revenue_net": walkin_rev, "bill_count": walkin_n},
        "previous_summary": {"revenue_net": 0.0, "customer_count": 0, "bill_count": 0},
        "by_branch": [{"key": k, **v} for k, v in sorted(by_branch.items())],
        "top_customers": top,
        "unmatched_customers": [r for r in top if not r["customer_name"]],
        "live": True,
        "freshness": "PARTS9 live",
        "named_bill_count": len(named),
    }


def product_overview(*, dfrom: str | None, dto: str | None, branch: str | None, limit: int = 50) -> dict[str, Any]:
    start, end = resolve_range(dfrom, dto)
    br = (branch or "").strip().upper() or None
    if br == "ALL":
        br = None
    lim = max(1, min(int(limit or 50), 200))
    bills = _bills_index(start, end, br)
    agg: dict[str, dict[str, Any]] = {}
    bill_seen: dict[str, set[str]] = defaultdict(set)
    cats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"key": "", "label": "", "revenue_net": 0.0, "base_qty": 0.0, "sku_count": 0, "_skus": set()}
    )
    by_branch: dict[str, dict[str, float | int]] = defaultdict(lambda: {"revenue_net": 0.0, "bill_count": 0})
    line_count = 0
    for ln in _sidet_lines(start, end):
        meta = bills.get(ln["billno"].upper())
        if not meta:
            continue
        code = ln["bcode"]
        row = agg.setdefault(
            code,
            {
                "bcode": code,
                "detail": ln["detail"] or code,
                "category_code": (code[:2] or "").zfill(2) if code else "",
                "category_name": "",
                "code1": None,
                "code1_name": None,
                "revenue_net": 0.0,
                "base_qty": 0.0,
                "line_count": 0,
                "bill_count": 0,
                "hq_revenue_net": 0.0,
                "syp_revenue_net": 0.0,
                "online_revenue_net": 0.0,
                "on_hand_qty": 0.0,
                "pcode": None,
                "mcode": None,
                "brand": None,
            },
        )
        if ln["detail"] and (not row["detail"] or row["detail"] == code):
            row["detail"] = ln["detail"]
        row["revenue_net"] += ln["amount"]
        row["base_qty"] += ln["qty"]
        row["line_count"] += ln["lines"]
        line_count += ln["lines"]
        row[{"HQ": "hq_revenue_net", "SYP": "syp_revenue_net", "ONLINE": "online_revenue_net"}[meta["branch"]]] += ln[
            "amount"
        ]
        bill_seen[code].add(ln["billno"].upper())
        cat = row["category_code"]
        c = cats[cat]
        c["key"] = cat
        c["label"] = cat
        c["revenue_net"] += ln["amount"]
        c["base_qty"] += ln["qty"]
        c["_skus"].add(code)
        by_branch[meta["branch"]]["revenue_net"] += ln["amount"]
        by_branch[meta["branch"]]["bill_count"] = by_branch[meta["branch"]].get("bill_count", 0)
    for code, row in agg.items():
        row["bill_count"] = len(bill_seen[code])
    for c in cats.values():
        c["sku_count"] = len(c.pop("_skus"))
    top = sorted(agg.values(), key=lambda r: -r["revenue_net"])[:lim]
    onhand = _icmas_on_hand([r["bcode"] for r in top])
    for r in top:
        r["on_hand_qty"] = onhand.get(r["bcode"], 0.0)
        r["category_name"] = r["category_code"]
    revenue = sum(r["revenue_net"] for r in agg.values())
    qty = sum(r["base_qty"] for r in agg.values())
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "branch": br,
        "limit": lim,
        "summary": {
            "revenue_net": revenue,
            "base_qty": qty,
            "sku_count": len(agg),
            "line_count": line_count,
            "bill_count": len(bills),
        },
        "previous_summary": {"revenue_net": 0.0, "base_qty": 0.0, "sku_count": 0},
        "by_category": sorted(
            ({k: v for k, v in c.items()} for c in cats.values()),
            key=lambda r: -r["revenue_net"],
        )[:20],
        "by_code1": [],
        "by_branch": [{"key": k, "revenue_net": v["revenue_net"], "bill_count": v["bill_count"]} for k, v in sorted(by_branch.items())],
        "top_products": top,
        "live": True,
        "freshness": "PARTS9 live",
    }


def product_movement(*, dfrom: str | None, dto: str | None, branch: str | None, stock_limit: int = 50) -> dict[str, Any]:
    start, end = resolve_range(dfrom, dto)
    br = (branch or "").strip().upper() or None
    if br == "ALL":
        br = None
    lim = max(1, min(int(stock_limit or 50), 200))
    bills = _bills_index(start, end, br)
    sell: dict[str, dict[str, Any]] = {}
    days: dict[str, set[str]] = defaultdict(set)
    billset: dict[str, set[str]] = defaultdict(set)
    for ln in _sidet_lines(start, end):
        meta = bills.get(ln["billno"].upper())
        if not meta:
            continue
        code = ln["bcode"]
        row = sell.setdefault(
            code,
            {
                "bcode": code,
                "detail": ln["detail"] or code,
                "category_code": (code[:2] or "").zfill(2) if code else "",
                "sell_qty": 0.0,
                "sell_bills": 0,
                "sell_days": 0,
                "buy_qty": 0.0,
                "buy_bills": 0,
                "on_hand_qty": 0.0,
                "last_sale_date": meta["billdate"],
                "last_purchase_date": None,
            },
        )
        row["sell_qty"] += ln["qty"]
        if ln["detail"]:
            row["detail"] = ln["detail"]
        billset[code].add(ln["billno"].upper())
        days[code].add(meta["billdate"])
        if meta["billdate"] > (row["last_sale_date"] or ""):
            row["last_sale_date"] = meta["billdate"]
    for code, row in sell.items():
        row["sell_bills"] = len(billset[code])
        row["sell_days"] = len(days[code])
        row["category_name"] = row["category_code"]
        row["code1"] = None
        row["code1_name"] = None

    buys: dict[str, dict[str, Any]] = {}
    engine = get_site_engine("hq")
    with engine.connect() as conn:
        for r in conn.execute(_BUY_SQL, {"dfrom": start.isoformat(), "dto": end.isoformat()}).mappings().all():
            code = str(r.get("BCODE") or "").strip()
            buys[code] = {"qty": _num(r.get("QTY")), "bills": int(r.get("BILLS") or 0), "detail": str(r.get("DETAIL") or "").strip()}
    for code, b in buys.items():
        if code in sell:
            sell[code]["buy_qty"] = b["qty"]
            sell[code]["buy_bills"] = b["bills"]
        else:
            sell.setdefault(
                code,
                {
                    "bcode": code,
                    "detail": b["detail"] or code,
                    "category_code": (code[:2] or "").zfill(2) if code else "",
                    "category_name": (code[:2] or "").zfill(2) if code else "",
                    "code1": None,
                    "code1_name": None,
                    "sell_qty": 0.0,
                    "sell_bills": 0,
                    "sell_days": 0,
                    "buy_qty": b["qty"],
                    "buy_bills": b["bills"],
                    "on_hand_qty": 0.0,
                    "last_sale_date": None,
                    "last_purchase_date": None,
                },
            )

    sold = [r for r in sell.values() if r["sell_qty"] > 0]
    stock_more = sorted(sold, key=lambda r: (-r["sell_qty"], -r["sell_bills"], r["bcode"]))[:lim]
    onhand = _icmas_on_hand([r["bcode"] for r in stock_more])
    for r in stock_more:
        r["on_hand_qty"] = onhand.get(r["bcode"], 0.0)
    bought = [r for r in sell.values() if r["buy_qty"] > 0]
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "branch": br,
        "mode": "stock_more",
        "stock_limit": lim,
        "dead_limit": 0,
        "dead_offset": 0,
        "dead_sort": "deep",
        "dead_tier": None,
        "dead_category": None,
        "dead_returned_count": 0,
        "dead_has_more": False,
        "summary": {
            "sold_sku_count": len(sold),
            "sell_qty": sum(r["sell_qty"] for r in sold),
            "bought_sku_count": len(bought),
            "buy_qty": sum(r["buy_qty"] for r in bought),
            "dead_yellow_count": 0,
            "dead_orange_count": 0,
            "dead_red_count": 0,
            "dead_total_count": 0,
            "dead_category_total": 0,
            "dead_stock_value": 0.0,
            "dead_category_stock_value": 0.0,
        },
        "stock_more": stock_more,
        "dead_stock": [],
        "live": True,
        "freshness": "PARTS9 live",
        "dead_note": "สต็อกค้าง (dead) ยังใช้สำเนาบน cloud เพราะต้องไล่ประวัติขายหลายปี — ไม่ยิง SIDET ย้อนหลังบน PARTS9",
    }
