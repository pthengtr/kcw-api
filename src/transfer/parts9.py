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


def _fetch_icmas_meta(
    engine: Engine, bcodes: list[str], *, include_blocked: bool = False
) -> dict[str, dict[str, Any]]:
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
            blocked = qtymin < 0
            if blocked and not include_blocked:
                continue
            out[bcode] = {
                "qtyoh2": _parse_qty(row["QTYOH2"]),
                "qtymin": qtymin,
                "blocked": blocked,
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


def lookup_transfer_product(*, bcode: str) -> dict[str, Any] | None:
    """Resolve BCODE to ICMAS display fields (HQ + SYP stock)."""
    code = (bcode or "").strip()
    if not code:
        return None
    hq_meta = _fetch_icmas_meta(get_site_engine("hq"), [code], include_blocked=True).get(code)
    syp_meta = _fetch_icmas_meta(get_site_engine("syp"), [code], include_blocked=True).get(code)
    if not hq_meta and not syp_meta:
        return None
    descr = ""
    ui1 = ""
    ui2 = ""
    mtp2 = 1.0
    for meta in (syp_meta, hq_meta):
        if not meta:
            continue
        if not descr and meta.get("descr"):
            descr = meta["descr"]
        if not ui1 and meta.get("ui1"):
            ui1 = meta["ui1"]
        if not ui2 and meta.get("ui2"):
            ui2 = meta["ui2"]
        if float(meta.get("mtp2") or 1.0) > 1.0:
            mtp2 = float(meta["mtp2"])
    blocked = bool((hq_meta or {}).get("blocked") or (syp_meta or {}).get("blocked"))
    return {
        "bcode": code,
        "descr": descr,
        "hq_qtyoh2": float((hq_meta or {}).get("qtyoh2") or 0),
        "syp_qtyoh2": float((syp_meta or {}).get("qtyoh2") or 0),
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
        "do_not_restock": blocked,
    }


def enrich_transfer_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill missing descr / stock hints from ICMAS for transfer line dicts."""
    missing = [
        (ln.get("bcode") or "").strip()
        for ln in lines
        if (ln.get("bcode") or "").strip() and not (ln.get("descr") or "").strip()
    ]
    if not missing:
        return lines
    codes = sorted(set(missing))
    hq_icmas = _fetch_icmas_meta(get_site_engine("hq"), codes, include_blocked=True)
    syp_icmas = _fetch_icmas_meta(get_site_engine("syp"), codes, include_blocked=True)
    out: list[dict[str, Any]] = []
    for ln in lines:
        row = dict(ln)
        bcode = (row.get("bcode") or "").strip()
        if bcode and not (row.get("descr") or "").strip():
            for meta in (syp_icmas.get(bcode), hq_icmas.get(bcode)):
                if meta and meta.get("descr"):
                    row["descr"] = meta["descr"]
                    break
        out.append(row)
    return out
