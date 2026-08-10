"""Everyday stock-count candidate selection (ABC + risk priorities)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.stock_check.parts9 import (
    ProductRow,
    get_parts9_engine,
    get_products_by_bcodes,
    list_negative_stock_products,
    list_never_counted_stock_products,
)

logger = logging.getLogger("kcw.stock_check.daily_pick")

BANGKOK = ZoneInfo("Asia/Bangkok")
REPEAT_GAP_DAYS = 14
ABC_CYCLE_DAYS = {"A": 21, "B": 45, "C": 90}

PRIORITY_NEGATIVE = 1
PRIORITY_MISMATCH = 2
PRIORITY_SA_ADJUST = 3
PRIORITY_YESTERDAY = 4
PRIORITY_ABC_DUE = 5
PRIORITY_NEVER = 6

_SALES_EXCLUDE_SQL = """
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE 'DN%'
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE 'TAR%'
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE '3TAR%'
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE 'TF%'
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE 'SA%'
  AND UPPER(LTRIM(RTRIM(m.BILLNO))) NOT LIKE '3SA%'
"""


@dataclass(frozen=True)
class SalesSignals:
    as_of: date
    yesterday_bcodes: frozenset[str]
    sales_days_90: dict[str, int]
    sa_bcodes: frozenset[str]


@dataclass
class CandidateFlags:
    negative_or_anomaly: bool = False
    prior_mismatch: bool = False
    prior_sa_adjust: bool = False
    sold_yesterday: bool = False
    abc_due: bool = False
    never_counted: bool = False
    abc_class: str = "N"
    sales_days_90: int = 0
    last_count_date: date | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def is_candidate(self) -> bool:
        return bool(
            self.negative_or_anomaly
            or self.prior_mismatch
            or self.prior_sa_adjust
            or self.sold_yesterday
            or self.abc_due
            or self.never_counted
        )

    @property
    def priority(self) -> int:
        if self.negative_or_anomaly:
            return PRIORITY_NEGATIVE
        if self.prior_mismatch:
            return PRIORITY_MISMATCH
        if self.prior_sa_adjust:
            return PRIORITY_SA_ADJUST
        if self.sold_yesterday:
            return PRIORITY_YESTERDAY
        if self.abc_due:
            return PRIORITY_ABC_DUE
        if self.never_counted:
            return PRIORITY_NEVER
        return 99


_signals_cache: SalesSignals | None = None


def bangkok_today(now: float | None = None) -> date:
    if now is None:
        return datetime.now(BANGKOK).date()
    return datetime.fromtimestamp(now, BANGKOK).date()


def abc_class(sales_days: int) -> str:
    days = max(0, int(sales_days))
    if days >= 30:
        return "A"
    if days >= 10:
        return "B"
    if days >= 1:
        return "C"
    return "N"


def is_abc_due(
    *,
    klass: str,
    last_count: date | None,
    today: date,
) -> bool:
    """A/B/C due by cycle. N is never cycle-due (only via risk / never pools)."""
    cycle = ABC_CYCLE_DAYS.get(klass)
    if cycle is None:
        return False
    if last_count is None:
        return True
    return (today - last_count).days >= cycle


def within_repeat_gap(
    last_count: date | None,
    today: date,
    *,
    gap_days: int = REPEAT_GAP_DAYS,
) -> bool:
    if last_count is None:
        return False
    return (today - last_count).days <= gap_days


def last_count_date_from_audit(audit: dict[str, Any] | None) -> date | None:
    if not audit:
        return None
    raw = audit.get("last_audited_at")
    if raw is None:
        return None
    try:
        ts = float(raw)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, BANGKOK).date()


def build_flags(
    *,
    product: ProductRow,
    audit: dict[str, Any] | None,
    signals: SalesSignals,
    today: date,
) -> CandidateFlags:
    bcode = product.bcode
    last_count = last_count_date_from_audit(audit)
    sales_days = int(signals.sales_days_90.get(bcode, 0))
    klass = abc_class(sales_days)
    negative = product.qtyoh2 < 0
    mismatch = bool(audit and str(audit.get("last_outcome") or "").lower() == "adjusted")
    prior_sa = bcode in signals.sa_bcodes
    yesterday = bcode in signals.yesterday_bcodes
    never = last_count is None
    due = is_abc_due(klass=klass, last_count=last_count, today=today)

    flags = CandidateFlags(
        negative_or_anomaly=negative,
        prior_mismatch=mismatch,
        prior_sa_adjust=prior_sa,
        sold_yesterday=yesterday,
        abc_due=due,
        never_counted=never,
        abc_class=klass,
        sales_days_90=sales_days,
        last_count_date=last_count,
    )
    reasons: list[str] = []
    if flags.negative_or_anomaly:
        reasons.append("negative_stock")
    if flags.prior_mismatch:
        reasons.append("prior_mismatch")
    if flags.prior_sa_adjust:
        reasons.append("prior_sa_adjust")
    if flags.sold_yesterday:
        reasons.append("sold_yesterday")
    if flags.abc_due:
        reasons.append(f"abc_due_{flags.abc_class}")
    if flags.never_counted:
        reasons.append("never_counted")
    flags.reasons = reasons
    return flags


def passes_repeat_gap(flags: CandidateFlags, today: date) -> bool:
    if flags.negative_or_anomaly:
        return True
    if within_repeat_gap(flags.last_count_date, today):
        return False
    return True


def clear_sales_signals_cache() -> None:
    global _signals_cache
    _signals_cache = None


def fetch_sales_signals(
    *,
    engine: Engine | None = None,
    today: date | None = None,
    force: bool = False,
) -> SalesSignals:
    global _signals_cache
    as_of = today or bangkok_today()
    if not force and _signals_cache is not None and _signals_cache.as_of == as_of:
        return _signals_cache

    eng = engine or get_parts9_engine(writer=False)
    # Use GETDATE() window on PARTS9 host (Thailand). ISO date literals caused hung plans.

    yesterday_sql = text(
        f"""
        SELECT DISTINCT LTRIM(RTRIM(d.BCODE)) AS bcode
        FROM dbo.SIDET d WITH (NOLOCK)
        INNER JOIN dbo.SIMAS m WITH (NOLOCK)
          ON d.BILLNO = m.BILLNO
         AND d.BILLDATE = m.BILLDATE
         AND d.BILLTYPE = m.BILLTYPE
         AND d.JOURMODE = m.JOURMODE
        WHERE CONVERT(date, m.BILLDATE) = DATEADD(day, -1, CONVERT(date, GETDATE()))
          AND UPPER(LTRIM(RTRIM(COALESCE(m.CANCELED,'')))) <> 'Y'
          AND LTRIM(RTRIM(COALESCE(m.JOURMODE,''))) <> '0'
          AND NULLIF(LTRIM(RTRIM(d.BCODE)), '') IS NOT NULL
          {_SALES_EXCLUDE_SQL}
        """
    )
    # TOP + ORDER BY is required — unbounded GROUP BY can hang on this PARTS9 host.
    sales_days_sql = text(
        f"""
        SELECT TOP 10000
          LTRIM(RTRIM(d.BCODE)) AS bcode,
          COUNT(DISTINCT CONVERT(date, m.BILLDATE)) AS sales_days
        FROM dbo.SIDET d WITH (NOLOCK)
        INNER JOIN dbo.SIMAS m WITH (NOLOCK)
          ON d.BILLNO = m.BILLNO
         AND d.BILLDATE = m.BILLDATE
         AND d.BILLTYPE = m.BILLTYPE
         AND d.JOURMODE = m.JOURMODE
        WHERE CONVERT(date, m.BILLDATE) >= DATEADD(day, -89, CONVERT(date, GETDATE()))
          AND CONVERT(date, m.BILLDATE) <= CONVERT(date, GETDATE())
          AND UPPER(LTRIM(RTRIM(COALESCE(m.CANCELED,'')))) <> 'Y'
          AND LTRIM(RTRIM(COALESCE(m.JOURMODE,''))) <> '0'
          AND NULLIF(LTRIM(RTRIM(d.BCODE)), '') IS NOT NULL
          {_SALES_EXCLUDE_SQL}
        GROUP BY LTRIM(RTRIM(d.BCODE))
        ORDER BY sales_days DESC, bcode
        """
    )
    sa_sql = text(
        """
        SELECT DISTINCT LTRIM(RTRIM(d.BCODE)) AS bcode
        FROM dbo.SIMAS m WITH (NOLOCK)
        INNER JOIN dbo.SIDET d WITH (NOLOCK)
          ON d.BILLNO = m.BILLNO
         AND d.BILLDATE = m.BILLDATE
         AND d.BILLTYPE = m.BILLTYPE
         AND d.JOURMODE = m.JOURMODE
        WHERE UPPER(LTRIM(RTRIM(COALESCE(m.CANCELED,'')))) <> 'Y'
          AND NULLIF(LTRIM(RTRIM(d.BCODE)), '') IS NOT NULL
          AND (
            UPPER(LTRIM(RTRIM(m.BILLNO))) LIKE 'SA%'
            OR UPPER(LTRIM(RTRIM(m.BILLNO))) LIKE '3SA%'
          )
          AND CONVERT(date, m.BILLDATE) >= DATEADD(year, -2, CONVERT(date, GETDATE()))
        """
    )

    t0 = time.time()
    with eng.connect() as conn:
        conn.execute(text("SET LOCK_TIMEOUT 20000"))
        yesterday_rows = conn.execute(yesterday_sql).mappings().fetchall()
        sales_rows = conn.execute(sales_days_sql).mappings().fetchall()
        sa_rows = conn.execute(sa_sql).mappings().fetchall()

    signals = SalesSignals(
        as_of=as_of,
        yesterday_bcodes=frozenset(
            str(r["bcode"]).strip() for r in yesterday_rows if r["bcode"]
        ),
        sales_days_90={
            str(r["bcode"]).strip(): int(r["sales_days"] or 0)
            for r in sales_rows
            if r["bcode"]
        },
        sa_bcodes=frozenset(str(r["bcode"]).strip() for r in sa_rows if r["bcode"]),
    )
    logger.info(
        "sales signals as_of=%s yesterday=%s sales90=%s sa=%s in %.2fs",
        as_of,
        len(signals.yesterday_bcodes),
        len(signals.sales_days_90),
        len(signals.sa_bcodes),
        time.time() - t0,
    )
    _signals_cache = signals
    return signals


def pick_daily_products(
    *,
    count: int,
    exclude_bcodes: set[str],
    audits: dict[str, dict[str, Any]],
    now: float | None = None,
    engine: Engine | None = None,
    signals: SalesSignals | None = None,
) -> list[tuple[ProductRow, CandidateFlags]]:
    """Build today's list: one row per SKU, highest matching priority wins."""
    count = max(1, min(int(count), 50))
    eng = engine or get_parts9_engine(writer=False)
    today = bangkok_today(now)
    sig = signals or fetch_sales_signals(engine=eng, today=today)

    audited = set(audits.keys())
    mismatch_bcodes = {
        b
        for b, row in audits.items()
        if str(row.get("last_outcome") or "").lower() == "adjusted"
    }

    seed_bcodes: set[str] = set()
    seed_bcodes |= set(sig.yesterday_bcodes)
    seed_bcodes |= set(sig.sa_bcodes)
    seed_bcodes |= mismatch_bcodes

    # ABC-due: rank by sales_days (higher first), cap how many we hydrate from ICMAS
    abc_due_ranked: list[tuple[int, str]] = []
    for bcode, days in sig.sales_days_90.items():
        klass = abc_class(days)
        last = last_count_date_from_audit(audits.get(bcode))
        if is_abc_due(klass=klass, last_count=last, today=today):
            abc_due_ranked.append((int(days), bcode))
    abc_due_ranked.sort(key=lambda item: (-item[0], item[1]))
    for _days, bcode in abc_due_ranked[: max(count * 20, 200)]:
        seed_bcodes.add(bcode)

    seed_bcodes -= exclude_bcodes

    products_by_code: dict[str, ProductRow] = {
        p.bcode: p for p in get_products_by_bcodes(seed_bcodes, engine=eng)
    }
    for product in list_negative_stock_products(exclude_bcodes=exclude_bcodes, engine=eng):
        products_by_code[product.bcode] = product

    for product in list_never_counted_stock_products(
        audited_bcodes=audited,
        exclude_bcodes=exclude_bcodes | set(products_by_code),
        limit=max(count * 4, 40),
        engine=eng,
    ):
        products_by_code[product.bcode] = product

    ranked: list[tuple[int, str, str, ProductRow, CandidateFlags]] = []
    for product in products_by_code.values():
        if product.bcode in exclude_bcodes:
            continue
        flags = build_flags(
            product=product,
            audit=audits.get(product.bcode),
            signals=sig,
            today=today,
        )
        if not flags.is_candidate:
            continue
        if not passes_repeat_gap(flags, today):
            continue
        ranked.append(
            (flags.priority, product.location1 or "", product.bcode, product, flags)
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))

    chosen: list[tuple[ProductRow, CandidateFlags]] = []
    used: set[str] = set()
    current_loc = ranked[0][1] if ranked else ""
    while len(chosen) < count and len(used) < len(ranked):
        best_idx = None
        best_key = None
        for idx, (prio, loc, bcode, _product, _flags) in enumerate(ranked):
            if bcode in used:
                continue
            key = (prio, 0 if (loc and loc == current_loc) else 1, idx)
            if best_key is None or key < best_key:
                best_key = key
                best_idx = idx
        if best_idx is None:
            break
        _prio, loc, bcode, product, flags = ranked[best_idx]
        chosen.append((product, flags))
        used.add(bcode)
        if loc:
            current_loc = loc

    return chosen
