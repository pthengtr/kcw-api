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
    """ICMAS qty/unit fields per BCODE; blocked=True when QTYMIN < 0 (do not restock)."""
    codes = sorted({c for c in bcodes if c})
    if not codes:
        return {}
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    sql = text(
        f"""
        SELECT
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR, ''))) AS descr,
          QTYOH2,
          QTYMIN,
          LTRIM(RTRIM(COALESCE(UI1, ''))) AS ui1,
          LTRIM(RTRIM(COALESCE(UI2, ''))) AS ui2,
          MTP2
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
            mtp2 = _parse_qty(row["MTP2"]) or 1.0
            out[bcode] = {
                "qtyoh2": _parse_qty(row["QTYOH2"]),
                "qtymin": qtymin,
                "blocked": qtymin < 0,
                "descr": (row["descr"] or "").strip(),
                "ui1": (row["ui1"] or "").strip(),
                "ui2": (row["ui2"] or "").strip(),
                "mtp2": mtp2 if mtp2 > 0 else 1.0,
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
            "hq_qtyoh2": 0.0,
            "syp_qtyoh2": 0.0,
            "qtymin": 0.0,
            "ui1": "",
            "ui2": "",
            "mtp2": 1.0,
        }

    bcodes = list(by_bcode)
    hq_icmas = _fetch_icmas_meta(get_site_engine("hq"), bcodes)
    syp_icmas = _fetch_icmas_meta(get_site_engine("syp"), bcodes)
    local_icmas = hq_icmas if site_key == "hq" else syp_icmas

    out: list[dict[str, Any]] = []
    for bcode in sorted(by_bcode):
        local_meta = local_icmas.get(bcode)
        if local_meta and local_meta.get("blocked"):
            continue
        item = by_bcode[bcode]
        hq_meta = hq_icmas.get(bcode)
        syp_meta = syp_icmas.get(bcode)
        if hq_meta:
            item["hq_qtyoh2"] = hq_meta["qtyoh2"]
        if syp_meta:
            item["syp_qtyoh2"] = syp_meta["qtyoh2"]
        for meta in (local_meta, hq_meta, syp_meta):
            if not meta:
                continue
            if not item.get("descr") and meta.get("descr"):
                item["descr"] = meta["descr"]
            if not item.get("ui1") and meta.get("ui1"):
                item["ui1"] = meta["ui1"]
            if not item.get("ui2") and meta.get("ui2"):
                item["ui2"] = meta["ui2"]
            if float(meta.get("mtp2") or 1.0) > 1.0:
                item["mtp2"] = float(meta["mtp2"])
        if local_meta:
            item["qtyoh2"] = local_meta["qtyoh2"]
            item["qtymin"] = local_meta["qtymin"]
        else:
            item["qtyoh2"] = item.get(f"{site_key}_qtyoh2", 0.0)
        out.append(item)

    return out[:lim]
