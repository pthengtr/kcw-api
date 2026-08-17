"""Live sales overview from HQ+SYP SIMAS (bill grain BEFORETAX)."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text

from src.ops.bi_filters import (
    billtype_std,
    channel,
    excluded_from_revenue,
    previous_range,
    reporting_branch,
    resolve_range,
    sales_type,
    _num,
)
from src.parts9_explorer.db import get_site_engine

_CACHE: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
_TTL = 45.0

_BILL_SQL = text(
    """
    SELECT
      LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) AS BILLNO,
      CONVERT(varchar(10), BILLDATE, 23) AS BILLDATE,
      BEFORETAX, TAX,
      LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(ACCTNO,'')))) AS ACCTNO,
      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME
    FROM dbo.SIMAS
    WHERE CONVERT(varchar(10), BILLDATE, 23) >= :dfrom
      AND CONVERT(varchar(10), BILLDATE, 23) <= :dto
      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'
      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(JOURMODE,'')))) <> '0'
    """
)


def _split() -> dict[str, dict[str, float | int]]:
    return defaultdict(lambda: {"revenue_net": 0.0, "bill_count": 0})


def fetch_revenue_bills(start: date, end: date) -> list[dict[str, Any]]:
    params = {"dfrom": start.isoformat(), "dto": end.isoformat()}
    out: list[dict[str, Any]] = []
    for site in ("hq", "syp"):
        engine = get_site_engine(site)
        with engine.connect() as conn:
            rows = conn.execute(_BILL_SQL, params).mappings().all()
        for r in rows:
            billno = str(r.get("BILLNO") or "").strip()
            if not billno or excluded_from_revenue(billno):
                continue
            std = billtype_std(billno)
            tax = _num(r.get("TAX"))
            out.append(
                {
                    "site": site,
                    "billno": billno,
                    "billdate": str(r.get("BILLDATE") or "")[:10],
                    "acctno": str(r.get("ACCTNO") or "").strip(),
                    "acctname": str(r.get("ACCTNAME") or "").strip(),
                    "revenue_net": _num(r.get("BEFORETAX")),
                    "vat_baht": tax,
                    "billtype_std": std,
                    "branch": reporting_branch(site=site, billno=billno, std=std),
                    "channel": channel(std, billno),
                    "sales_type": sales_type(std, billno, tax),
                }
            )
    return out


def _summarize(bills: list[dict[str, Any]], branch: str | None) -> dict[str, Any]:
    rows = [b for b in bills if branch is None or b["branch"] == branch]
    revenue = sum(b["revenue_net"] for b in rows)
    vat = sum(b["vat_baht"] for b in rows)
    n = len(rows)
    by_sales = _split()
    by_branch = _split()
    by_channel = _split()
    by_billtype = _split()
    daily: dict[str, dict[str, Any]] = {}
    monthly: dict[str, dict[str, Any]] = {}

    def bump_period(bucket: dict[str, dict[str, Any]], period: str, bill: dict[str, Any]) -> None:
        row = bucket.setdefault(
            period,
            {
                "period": period,
                "revenue_net": 0.0,
                "bill_count": 0,
                "hq_revenue_net": 0.0,
                "syp_revenue_net": 0.0,
                "online_revenue_net": 0.0,
            },
        )
        row["revenue_net"] += bill["revenue_net"]
        row["bill_count"] += 1
        key = {"HQ": "hq_revenue_net", "SYP": "syp_revenue_net", "ONLINE": "online_revenue_net"}.get(
            bill["branch"]
        )
        if key:
            row[key] += bill["revenue_net"]

    for b in rows:
        for group, key in (
            (by_sales, b["sales_type"]),
            (by_branch, b["branch"]),
            (by_channel, b["channel"]),
            (by_billtype, b["billtype_std"]),
        ):
            group[key]["revenue_net"] += b["revenue_net"]
            group[key]["bill_count"] += 1
        bump_period(daily, b["billdate"], b)
        bump_period(monthly, b["billdate"][:7], b)

    def as_list(src: dict[str, dict[str, float | int]], *, revenue_desc: bool = False) -> list[dict[str, Any]]:
        items = [{"key": k, **v} for k, v in src.items()]
        items.sort(key=(lambda x: -float(x["revenue_net"])) if revenue_desc else (lambda x: str(x["key"])))
        return items

    return {
        "summary": {
            "revenue_net": revenue,
            "vat_baht": vat,
            "bill_count": n,
            "avg_bill": (revenue / n) if n else 0.0,
        },
        "by_sales_type": as_list(by_sales),
        "by_branch": as_list(by_branch),
        "by_channel": as_list(by_channel),
        "by_billtype": as_list(by_billtype, revenue_desc=True),
        "trend_daily": [daily[k] for k in sorted(daily)],
        "trend_monthly": [monthly[k] for k in sorted(monthly)],
        "bills": rows,
    }


def sales_overview(*, dfrom: str | None, dto: str | None, branch: str | None) -> dict[str, Any]:
    start, end = resolve_range(dfrom, dto)
    br = (branch or "").strip().upper() or None
    if br == "ALL":
        br = None
    if br and br not in ("HQ", "SYP", "ONLINE"):
        raise ValueError("invalid branch")
    cache_key = (start.isoformat(), end.isoformat(), br or "ALL")
    now = time.monotonic()
    hit = _CACHE.get(cache_key)
    if hit and now - hit[0] < _TTL:
        return hit[1]

    prev_from, prev_to = previous_range(start, end)
    current = _summarize(fetch_revenue_bills(start, end), br)
    previous = _summarize(fetch_revenue_bills(prev_from, prev_to), br)
    payload = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "branch": br,
        "previous_from": prev_from.isoformat(),
        "previous_to": prev_to.isoformat(),
        "summary": current["summary"],
        "previous_summary": {
            "revenue_net": previous["summary"]["revenue_net"],
            "vat_baht": previous["summary"]["vat_baht"],
            "bill_count": previous["summary"]["bill_count"],
        },
        "by_sales_type": current["by_sales_type"],
        "by_branch": current["by_branch"],
        "by_channel": current["by_channel"],
        "by_billtype": current["by_billtype"],
        "trend_daily": current["trend_daily"],
        "trend_monthly": current["trend_monthly"],
        "live": True,
        "freshness": "PARTS9 live",
    }
    slim = dict(payload)
    _CACHE[cache_key] = (now, slim)
    return slim
