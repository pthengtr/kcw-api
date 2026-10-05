"""FIFO cost for the PARTS9 explorer.

The rebuild lives in Postgres schema ``fifo`` under ``site = hq`` only.
SYP stock is transferred from HQ, so branch sale lines use that same
yearly unit cost instead of a separate branch allocation.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text

from src.db.engine import get_engine

log = logging.getLogger(__name__)

FIFO_SITE = "hq"
QTY_EPS = 1e-9
_COSTED = ("OK", "PARTIAL")


def last_calendar_years(n: int = 5, *, today: date | None = None) -> list[int]:
    year = (today or date.today()).year
    count = max(1, int(n))
    return list(range(year - count + 1, year + 1))


def build_yearly(groups: list[dict[str, Any]], *, years: list[int]) -> list[dict[str, Any]]:
    """Weighted FIFO unit cost per calendar year.

    The average uses OK and PARTIAL lines only. ``units`` is every sale unit
    in the year, including UNCOSTED, so ``uncosted_share`` has a denominator.
    """
    buckets = {
        year: {"costed_units": 0.0, "costed_ext": 0.0, "all_units": 0.0, "uncosted_units": 0.0}
        for year in years
    }
    for group in groups:
        year = _int(group.get("yr"))
        if year not in buckets:
            continue
        units = _float(group.get("units")) or 0.0
        bucket = buckets[year]
        bucket["all_units"] += units
        status = str(group.get("status") or "")
        if status == "UNCOSTED":
            bucket["uncosted_units"] += units
        elif status in _COSTED:
            bucket["costed_units"] += units
            bucket["costed_ext"] += _float(group.get("ext")) or 0.0
    rows: list[dict[str, Any]] = []
    for year in years:
        bucket = buckets[year]
        unit = None
        if bucket["costed_units"] > QTY_EPS:
            unit = bucket["costed_ext"] / bucket["costed_units"]
        share = None
        if bucket["all_units"] > QTY_EPS:
            share = bucket["uncosted_units"] / bucket["all_units"]
        rows.append(
            {
                "year": year,
                "unit_cost": _round(unit, 4),
                "units": _round(bucket["all_units"], 4),
                "ext_cost": _round(bucket["costed_ext"], 2),
                "uncosted_share": _round(share, 4),
            }
        )
    return rows


def compare_pct(fifo_unit: float | None, other: float | None) -> float | None:
    """Percent by which FIFO differs from an older unit cost: (FIFO − old) / old."""
    if fifo_unit is None or other is None or abs(other) <= QTY_EPS:
        return None
    return round((float(fifo_unit) - float(other)) / abs(float(other)) * 100.0, 1)


def build_benchmarks(
    on_hand_unit: float | None,
    costlast: float | None,
    insight_avg_buy: float | None,
) -> dict[str, Any]:
    """Old costs to set beside FIFO.

    ``costlast`` is ICMAS.COSTLAST (last receipt cost).
    ``insight_avg_buy`` is the 12-month vendor-bill average shown as ราคาซื้อเฉลี่ย.
    """
    last = _round(_float(costlast), 4)
    buy = _round(_float(insight_avg_buy), 4)
    return {
        "costlast": last,
        "insight_avg_buy": buy,
        "vs_on_hand": {
            "costlast_pct": compare_pct(on_hand_unit, last),
            "insight_avg_buy_pct": compare_pct(on_hand_unit, buy),
        },
    }


def annotate_yearly(
    yearly: list[dict[str, Any]],
    costlast: float | None,
    costavg: float | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in yearly:
        item = dict(row)
        item["vs_costlast_pct"] = compare_pct(row.get("unit_cost"), costlast)
        item["vs_costavg_pct"] = compare_pct(row.get("unit_cost"), costavg)
        out.append(item)
    return out


def insight_avg_buy(insight: dict[str, Any] | None) -> float | None:
    body = ((insight or {}).get("insight") or {}) if isinstance(insight, dict) else {}
    derived = body.get("derived") or {}
    dashboard = body.get("dashboard") or derived.get("dashboard") or {}
    margin = body.get("margin") or derived.get("margin") or {}
    price_margin = dashboard.get("price_margin") or {}
    for value in (price_margin.get("avg_buy"), margin.get("avg_buy_12m")):
        number = _float(value)
        if number is not None:
            return number
    return None


def attach_line_costs(
    site: str,
    sales: list[dict[str, Any]],
    exact: dict[int, dict[str, Any]],
    yearly: list[dict[str, Any]],
    on_hand_unit: float | None,
    *,
    costlast: float | None = None,
    costavg: float | None = None,
) -> list[dict[str, Any]]:
    """Copy each sale row and add FIFO_UNIT, FIFO_EXT, FIFO_STATUS, MARGIN.

    HQ uses the rebuilt line. SYP uses that sale year's HQ weighted average,
    then the remaining on-hand unit cost when the year has no costed HQ sales.
    """
    year_cost = {int(row["year"]): row.get("unit_cost") for row in yearly}
    site_key = (site or FIFO_SITE).strip().lower() or FIFO_SITE
    out: list[dict[str, Any]] = []
    for sale in sales:
        row = dict(sale)
        unit = None
        ext = None
        status = None
        if site_key == FIFO_SITE:
            sid = _int(sale.get("ID"))
            hit = exact.get(sid) if sid is not None else None
            if hit:
                unit = _float(hit.get("fifo_unit_cost"))
                ext = _float(hit.get("fifo_ext_cost"))
                status = str(hit.get("status") or "") or None
        else:
            year = _year(sale.get("BILLDATE"))
            shared = year_cost.get(year) if year is not None else None
            if shared is None:
                shared = on_hand_unit
            qty = _float(sale.get("QTY"))
            if shared is not None and qty is not None:
                unit = float(shared)
                ext = round(unit * qty, 2)
                status = "HQ"
        row["FIFO_UNIT"] = _round(unit, 4)
        row["FIFO_EXT"] = _round(ext, 2)
        row["FIFO_STATUS"] = status
        row["MARGIN"] = _margin(_float(sale.get("AMOUNT")), row["FIFO_EXT"])
        row["VS_LAST"] = compare_pct(row["FIFO_UNIT"], costlast)
        row["VS_AVG"] = compare_pct(row["FIFO_UNIT"], costavg)
        out.append(row)
    return out


def fifo_for_product(
    bcode: str,
    *,
    site: str,
    sales: list[dict[str, Any]] | None = None,
    today: date | None = None,
    insight_avg_buy: float | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return ``(card, sales)``. ``card`` is None when Postgres cannot be read."""
    rows = list(sales or [])
    code = (bcode or "").strip()
    if not code:
        return {"found": False}, rows
    try:
        years = last_calendar_years(5, today=today)
        product, groups, exact = _load(code, site, rows, years)
    except Exception:
        log.exception("fifo lookup failed for %s", code)
        return None, rows
    if product is None:
        return {"found": False}, rows
    costlast = _hq_costlast(code)
    on_hand = product.get("on_hand_unit_cost")
    benchmarks = build_benchmarks(on_hand, costlast, insight_avg_buy)
    # Year and sale-line comparison uses the 12-month buy average insight shows.
    yearly = annotate_yearly(
        build_yearly(groups, years=years),
        benchmarks["costlast"],
        benchmarks["insight_avg_buy"],
    )
    enriched = attach_line_costs(
        site,
        rows,
        exact,
        yearly,
        on_hand,
        costlast=benchmarks["costlast"],
        costavg=benchmarks["insight_avg_buy"],
    )
    card = {
        "found": True,
        "shared_cost": (site or FIFO_SITE).strip().lower() != FIFO_SITE,
        "rebuilt_at": product.get("rebuilt_at"),
        "product": {key: value for key, value in product.items() if key != "rebuilt_at"},
        "benchmarks": benchmarks,
        "yearly": yearly,
    }
    return card, enriched


def _hq_costlast(bcode: str) -> float | None:
    """HQ ICMAS last receipt cost. Missing or unreadable values stay empty."""
    try:
        from src.parts9_explorer.db import get_site_engine

        with get_site_engine(FIFO_SITE).connect() as conn:
            row = conn.execute(_MASTER_SQL, {"bcode": bcode}).mappings().first()
    except Exception:
        log.exception("ICMAS cost lookup failed for %s", bcode)
        return None
    if row is None:
        return None
    return _float(row.get("costlast"))


def _load(
    bcode: str,
    site: str,
    sales: list[dict[str, Any]],
    years: list[int],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[int, dict[str, Any]]]:
    start = date(years[0], 1, 1)
    end = date(years[-1] + 1, 1, 1)
    engine = get_engine()
    with engine.connect() as conn:
        product_row = conn.execute(_PRODUCT_SQL, {"bcode": bcode}).mappings().first()
        if product_row is None:
            return None, [], {}
        groups = [dict(row) for row in conn.execute(
            _YEARLY_SQL, {"bcode": bcode, "start": start, "end_exclusive": end}
        ).mappings().all()]
        exact: dict[int, dict[str, Any]] = {}
        if (site or FIFO_SITE).strip().lower() == FIFO_SITE:
            ids = [sid for sid in (_int(row.get("ID")) for row in sales) if sid is not None]
            if ids:
                for row in conn.execute(_LINES_SQL, {"ids": ids}).mappings().all():
                    sid = _int(row.get("sidet_id"))
                    if sid is None:
                        continue
                    exact[sid] = {
                        "fifo_unit_cost": _float(row.get("fifo_unit_cost")),
                        "fifo_ext_cost": _float(row.get("fifo_ext_cost")),
                        "status": row.get("status"),
                    }
    return _product_card(product_row), groups, exact


def _product_card(row: Any) -> dict[str, Any]:
    covered = _float(row.get("on_hand_covered_qty")) or 0.0
    value = _float(row.get("on_hand_value")) or 0.0
    unit = (value / covered) if covered > QTY_EPS else None
    return {
        "on_hand_qty": _round(_float(row.get("on_hand_qty")), 4),
        "on_hand_covered_qty": _round(covered, 4),
        "on_hand_value": _round(value, 2),
        "on_hand_unit_cost": _round(unit, 4),
        "unassigned_qty": _round(_float(row.get("unassigned_qty")), 4),
        "cost_complete": bool(row.get("cost_complete")),
        "history_window": str(row.get("history_window") or ""),
        "qtyoh2_stale": bool(row.get("qtyoh2_stale")),
        "rebuilt_at": _fmt_rebuilt(row.get("rebuilt_at")),
    }


def _margin(amount: float | None, ext: float | None) -> float | None:
    if amount is None or ext is None or abs(amount) <= QTY_EPS:
        return None
    return round((amount - ext) / amount * 100.0, 1)


def _fmt_rebuilt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        stamp = value.astimezone(timezone.utc) if value.tzinfo else value
        return stamp.strftime("%Y-%m-%d %H:%M UTC")
    return str(value)


def _year(value: Any) -> int | None:
    text_value = str(value or "").strip()
    if len(text_value) < 4:
        return None
    return _int(text_value[:4])


def _int(value: Any) -> int | None:
    number = _float(value)
    if number is None:
        return None
    return int(number)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _round(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


_MASTER_SQL = text(
    """
    SELECT TOP 1 COSTLAST AS costlast
    FROM dbo.ICMAS
    WHERE LTRIM(RTRIM(BCODE)) = :bcode
    """
)

_PRODUCT_SQL = text(
    """
    SELECT
        on_hand_qty,
        on_hand_covered_qty,
        on_hand_value,
        unassigned_qty,
        history_window,
        cost_complete,
        qtyoh2_stale,
        rebuilt_at
    FROM fifo.product
    WHERE site = 'hq' AND bcode = :bcode
    """
)

_YEARLY_SQL = text(
    """
    SELECT
        EXTRACT(YEAR FROM sale_billdate)::int AS yr,
        status,
        SUM(units) AS units,
        SUM(fifo_ext_cost) AS ext
    FROM fifo.sale_cost
    WHERE site = 'hq'
      AND bcode = :bcode
      AND sale_billdate >= :start
      AND sale_billdate < :end_exclusive
    GROUP BY 1, 2
    """
)

_LINES_SQL = text(
    """
    SELECT sidet_id, fifo_unit_cost, fifo_ext_cost, status
    FROM fifo.sale_cost
    WHERE site = 'hq' AND sidet_id IN :ids
    """
).bindparams(bindparam("ids", expanding=True))
