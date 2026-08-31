from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.ops.iclow import list_iclow
from src.parts9_explorer.db import get_site_engine


def _parse_qty(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _fetch_icmas_meta(engine: Engine, bcodes: list[str]) -> dict[str, dict[str, Any]]:
    """ICMAS qty fields per BCODE; blocked=True when QTYMIN < 0 (do not restock)."""
    codes = sorted({c for c in bcodes if c})
    if not codes:
        return {}
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    sql = text(
        f"""
        SELECT
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          QTYOH2,
          QTYMIN
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})
        """
    )
    out: dict[str, dict[str, Any]] = {}
    with engine.connect() as conn:
        for row in conn.execute(sql, params).mappings().all():
            bcode = (row["bcode"] or "").strip()
            if not bcode:
                continue
            qtymin = _parse_qty(row["QTYMIN"])
            out[bcode] = {
                "qtyoh2": _parse_qty(row["QTYOH2"]),
                "qtymin": qtymin,
                "blocked": qtymin < 0,
            }
    return out


def suggest_transfer_skus(*, site: str, limit: int = 200) -> list[dict[str, Any]]:
    """ICLOW รอสั่งซื้อ — same source as legacy /po ICLOW tab (to_be_ordered)."""
    site_key = (site or "hq").strip().lower()
    lim = max(1, min(int(limit or 200), 200))
    scan = min(max(lim * 4, lim), 800)
    data = list_iclow(site=site_key, status="to_be_ordered", limit=scan, offset=0)

    by_bcode: dict[str, dict[str, Any]] = {}
    for row in data.get("rows") or []:
        bcode = (row.get("bcode") or "").strip()
        if not bcode:
            continue
        qty = _parse_qty(row.get("qty") or row.get("ordered_qty"))
        if bcode in by_bcode:
            by_bcode[bcode]["suggest_qty"] += qty
            continue
        by_bcode[bcode] = {
            "bcode": bcode,
            "descr": (row.get("descr") or "").strip(),
            "suggest_qty": qty,
            "qtyoh2": 0.0,
            "qtymin": 0.0,
            "qtyget": 0.0,
        }

    icmas = _fetch_icmas_meta(get_site_engine(site_key), list(by_bcode))

    out: list[dict[str, Any]] = []
    for bcode in sorted(by_bcode):
        meta = icmas.get(bcode)
        if meta and meta.get("blocked"):
            continue
        item = by_bcode[bcode]
        if meta:
            item["qtyoh2"] = meta["qtyoh2"]
            item["qtymin"] = meta["qtymin"]
        out.append(item)

    return out[:lim]
