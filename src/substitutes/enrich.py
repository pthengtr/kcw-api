"""ICMAS dual-site enrichment for substitute members (shared by Explorer + Transfer)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine

EngineFactory = Callable[[str], Any]


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fetch_site_rows(
    bcodes: list[str],
    *,
    site: str,
    get_engine: EngineFactory = get_site_engine,
) -> dict[str, dict[str, Any]]:
    codes = [c.strip() for c in bcodes if (c or "").strip()]
    if not codes:
        return {}
    try:
        engine = get_engine(site)
    except Exception:
        return {}
    placeholders = ", ".join(f":b{i}" for i in range(len(codes)))
    params = {f"b{i}": code for i, code in enumerate(codes)}
    sql = text(
        f"SELECT LTRIM(RTRIM(BCODE)) AS BCODE,"
        f" LTRIM(RTRIM(COALESCE(DESCR,''))) AS DESCR,"
        f" QTYOH2, QTYMIN"
        f" FROM dbo.ICMAS WHERE LTRIM(RTRIM(BCODE)) IN ({placeholders})"
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("BCODE") or "").strip()
        if not code:
            continue
        qty = _parse_float(row.get("QTYOH2"))
        qtymin = _parse_float(row.get("QTYMIN"))
        out[code] = {
            "descr": str(row.get("DESCR") or "").strip(),
            "qtyoh2": qty if qty is not None else 0.0,
            "qtymin": qtymin if qtymin is not None else 0.0,
        }
    return out


def fetch_dual_stock(
    bcodes: list[str],
    *,
    get_engine: EngineFactory = get_site_engine,
) -> dict[str, dict[str, Any]]:
    """Map bcode → descr + HQ/SYP qtyoh2/qtymin (missing site → null qty fields)."""
    codes = sorted({c.strip() for c in bcodes if (c or "").strip()})
    if not codes:
        return {}
    hq = _fetch_site_rows(codes, site="hq", get_engine=get_engine)
    syp = _fetch_site_rows(codes, site="syp", get_engine=get_engine)
    out: dict[str, dict[str, Any]] = {}
    for code in codes:
        h = hq.get(code)
        s = syp.get(code)
        descr = ""
        if h and h.get("descr"):
            descr = h["descr"]
        elif s and s.get("descr"):
            descr = s["descr"]
        out[code] = {
            "bcode": code,
            "descr": descr,
            "hq_qtyoh2": h["qtyoh2"] if h else None,
            "hq_qtymin": h["qtymin"] if h else None,
            "syp_qtyoh2": s["qtyoh2"] if s else None,
            "syp_qtymin": s["qtymin"] if s else None,
            "exists_hq": h is not None,
            "exists_syp": s is not None,
        }
    return out


def bcode_exists_any_site(
    bcode: str,
    *,
    get_engine: EngineFactory = get_site_engine,
) -> bool:
    code = (bcode or "").strip()
    if not code:
        return False
    info = fetch_dual_stock([code], get_engine=get_engine).get(code) or {}
    return bool(info.get("exists_hq") or info.get("exists_syp"))


def enrich_member_rows(
    members: list[dict[str, Any]],
    *,
    get_engine: EngineFactory = get_site_engine,
) -> list[dict[str, Any]]:
    """Attach dual stock fields; preserve sort_rank / note / group_id."""
    codes = [str(m.get("bcode") or "").strip() for m in members]
    stock = fetch_dual_stock(codes, get_engine=get_engine)
    enriched: list[dict[str, Any]] = []
    for m in members:
        row = dict(m)
        code = str(row.get("bcode") or "").strip()
        info = stock.get(code) or {
            "bcode": code,
            "descr": "",
            "hq_qtyoh2": None,
            "hq_qtymin": None,
            "syp_qtyoh2": None,
            "syp_qtymin": None,
        }
        row["bcode"] = code
        row["descr"] = info.get("descr") or ""
        row["hq_qtyoh2"] = info.get("hq_qtyoh2")
        row["hq_qtymin"] = info.get("hq_qtymin")
        row["syp_qtyoh2"] = info.get("syp_qtyoh2")
        row["syp_qtymin"] = info.get("syp_qtymin")
        row["sort_rank"] = int(row.get("sort_rank") or 0)
        hq_min = row.get("hq_qtymin")
        syp_min = row.get("syp_qtymin")
        row["hq_l1"] = hq_min is not None and float(hq_min) < 0
        row["syp_l1"] = syp_min is not None and float(syp_min) < 0
        enriched.append(row)
    return enriched


def enrich_group(
    group: dict[str, Any] | None,
    *,
    get_engine: EngineFactory = get_site_engine,
) -> dict[str, Any] | None:
    if not group:
        return None
    out = dict(group)
    out["members"] = enrich_member_rows(list(group.get("members") or []), get_engine=get_engine)
    return out
