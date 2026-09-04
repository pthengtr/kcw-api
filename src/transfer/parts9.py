from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.ops.iclow import list_iclow
from src.parts9_explorer.db import get_site_engine, site_sql_hosts_collide
from src.stock_check.auth import mint_access_token
from src.transfer.config import get_transfer_settings
from src.transfer.ui import APP, SESSION_COOKIE

logger = logging.getLogger(__name__)


def _parse_qty(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _format_location(loc1: Any, loc2: Any) -> str:
    parts = [str(v or "").strip() for v in (loc1, loc2)]
    return " / ".join(p for p in parts if p)


def _peer_request_headers() -> dict[str, str]:
    """Cookie token so peer works even when hostname resolves to LAN/loopback (not Tailscale CGNAT)."""
    settings = get_transfer_settings()
    headers = {"Accept": "application/json"}
    secret = (settings.token_secret or "").strip()
    if not secret:
        return headers
    token = mint_access_token(
        secret=secret,
        line_user_id="transfer-peer",
        display_name="transfer-peer",
        branch=settings.site,
        ttl_seconds=300,
        app=APP,
    )
    headers["Cookie"] = f"{SESSION_COOKIE}={token}"
    return headers


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
          LTRIM(RTRIM(COALESCE(MODEL, ''))) AS model,
          QTYOH2,
          QTYMIN,
          LTRIM(RTRIM(COALESCE(UI1, ''))) AS ui1,
          LTRIM(RTRIM(COALESCE(UI2, ''))) AS ui2,
          MTP2,
          LTRIM(RTRIM(COALESCE(LOCATION1, ''))) AS location1,
          LTRIM(RTRIM(COALESCE(LOCATION2, ''))) AS location2
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
            loc1 = (row["location1"] or "").strip()
            loc2 = (row["location2"] or "").strip()
            out[bcode] = {
                "qtyoh2": _parse_qty(row["QTYOH2"]),
                "qtymin": qtymin,
                "blocked": blocked,
                "descr": (row["descr"] or "").strip(),
                "model": (row["model"] or "").strip(),
                "ui1": (row["ui1"] or "").strip(),
                "ui2": (row["ui2"] or "").strip(),
                "mtp2": mtp2 if mtp2 > 0 else 1.0,
                "location1": loc1,
                "location2": loc2,
                "location": _format_location(loc1, loc2),
            }
    return out


def fetch_local_icmas_meta(
    bcodes: list[str], *, include_blocked: bool = True
) -> dict[str, dict[str, Any]]:
    """ICMAS from this box's TRANSFER_SITE PARTS9 only (peer endpoint / local half of dual stock)."""
    site_key = get_transfer_settings().site.lower()
    if site_key not in ("hq", "syp"):
        site_key = "hq"
    return _fetch_icmas_meta(
        get_site_engine(site_key), bcodes, include_blocked=include_blocked
    )


def _should_use_peer_for_site(site_key: str) -> bool:
    """Use peer when HQ/SYP SQL hosts collide — direct SQL would return the wrong branch's stock."""
    key = (site_key or "").strip().lower()
    local = get_transfer_settings().site.lower()
    if key == local:
        return False
    return site_sql_hosts_collide()


def _fetch_icmas_via_peer(
    bcodes: list[str], *, include_blocked: bool = True
) -> dict[str, dict[str, Any]]:
    codes = sorted({c for c in bcodes if c})
    if not codes:
        return {}
    base = get_transfer_settings().peer_base_url
    qs = urllib.parse.urlencode(
        {
            "bcodes": ",".join(codes),
            "include_blocked": "1" if include_blocked else "0",
        }
    )
    url = f"{base}/transfer/api/local-icmas?{qs}"
    req = urllib.request.Request(url, headers=_peer_request_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("transfer peer ICMAS fetch failed (%s): %s", url, exc)
        return {}
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for bcode, meta in items.items():
        code = (bcode or "").strip()
        if not code or not isinstance(meta, dict):
            continue
        loc1 = (meta.get("location1") or "").strip()
        loc2 = (meta.get("location2") or "").strip()
        loc = (meta.get("location") or "").strip() or _format_location(loc1, loc2)
        out[code] = {
            "qtyoh2": _parse_qty(meta.get("qtyoh2")),
            "qtymin": _parse_qty(meta.get("qtymin")),
            "blocked": bool(meta.get("blocked")),
            "descr": (meta.get("descr") or "").strip(),
            "model": (meta.get("model") or "").strip(),
            "ui1": (meta.get("ui1") or "").strip(),
            "ui2": (meta.get("ui2") or "").strip(),
            "mtp2": float(meta.get("mtp2") or 1.0) or 1.0,
            "location1": loc1,
            "location2": loc2,
            "location": loc,
        }
    return out


def _fetch_site_icmas(
    site_key: str, bcodes: list[str], *, include_blocked: bool = True
) -> dict[str, dict[str, Any]]:
    """Fetch ICMAS for one site — direct SQL, or peer HTTP when hosts collide / SQL down."""
    key = (site_key or "hq").strip().lower()
    if key not in ("hq", "syp"):
        key = "hq"
    if _should_use_peer_for_site(key):
        return _fetch_icmas_via_peer(bcodes, include_blocked=include_blocked)
    try:
        return _fetch_icmas_meta(
            get_site_engine(key), bcodes, include_blocked=include_blocked
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "direct ICMAS fetch failed for %s (%s); trying peer", key, exc
        )
        return _fetch_icmas_via_peer(bcodes, include_blocked=include_blocked)


def _fetch_dual_icmas(
    bcodes: list[str], *, include_blocked: bool = True
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    return (
        _fetch_site_icmas("hq", bcodes, include_blocked=include_blocked),
        _fetch_site_icmas("syp", bcodes, include_blocked=include_blocked),
    )


_ICLOW_PAGE_SIZE = 200
_ICMAS_EXTRA_LIMIT = 50


def _fetch_all_iclow_to_be_ordered(site_key: str) -> list[dict[str, Any]]:
    """Paginate list_iclow so suggest covers the full รอสั่งซื้อ tab, not just the first page."""
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None
    while True:
        data = list_iclow(
            site=site_key,
            status="to_be_ordered",
            limit=_ICLOW_PAGE_SIZE,
            offset=offset,
        )
        batch = list(data.get("rows") or [])
        if total is None:
            total = int(data.get("count") or len(batch))
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
        offset += _ICLOW_PAGE_SIZE
    return rows


def _enrich_suggest_item(
    item: dict[str, Any],
    *,
    site_key: str,
    hq_icmas: dict[str, dict[str, Any]],
    syp_icmas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    bcode = item["bcode"]
    local_icmas = hq_icmas if site_key == "hq" else syp_icmas
    local_meta = local_icmas.get(bcode)
    hq_meta = hq_icmas.get(bcode)
    syp_meta = syp_icmas.get(bcode)
    if hq_meta:
        item["hq_qtyoh2"] = hq_meta["qtyoh2"]
        item["hq_qtymin"] = hq_meta["qtymin"]
        item["hq_no_stock"] = bool(hq_meta.get("blocked"))
        item["location_hq"] = (hq_meta.get("location") or "").strip()
    else:
        item["hq_qtymin"] = None
        item["hq_no_stock"] = False
        item["location_hq"] = ""
    if syp_meta:
        item["syp_qtyoh2"] = syp_meta["qtyoh2"]
        item["location_syp"] = (syp_meta.get("location") or "").strip()
    else:
        item["location_syp"] = ""
    for meta in (local_meta, hq_meta, syp_meta):
        if not meta:
            continue
        if not item.get("descr") and meta.get("descr"):
            item["descr"] = meta["descr"]
        if not item.get("model") and meta.get("model"):
            item["model"] = meta["model"]
        if not item.get("ui1") and meta.get("ui1"):
            item["ui1"] = meta["ui1"]
        if not item.get("ui2") and meta.get("ui2"):
            item["ui2"] = meta["ui2"]
        if float(meta.get("mtp2") or 1.0) > 1.0:
            item["mtp2"] = float(meta["mtp2"])
    if local_meta:
        item["qtyoh2"] = local_meta["qtyoh2"]
        item["qtymin"] = local_meta["qtymin"]
        item["location"] = (local_meta.get("location") or "").strip()
        item["location1"] = (local_meta.get("location1") or "").strip()
        item["location2"] = (local_meta.get("location2") or "").strip()
    else:
        item["qtyoh2"] = item.get(f"{site_key}_qtyoh2", 0.0)
        item["location"] = item.get(f"location_{site_key}", "") or ""
    return item


def _suggest_from_icmas_low_stock(engine: Engine, *, limit: int) -> dict[str, dict[str, Any]]:
    """Requester-site ICMAS rows at/below min — covers re-order after ICLOW already stamped."""
    sql = text(
        """
        SELECT TOP (:lim)
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR, ''))) AS descr,
          LTRIM(RTRIM(COALESCE(MODEL, ''))) AS model,
          QTYOH2,
          QTYMIN,
          QTYGET,
          LTRIM(RTRIM(COALESCE(UI1, ''))) AS ui1,
          LTRIM(RTRIM(COALESCE(UI2, ''))) AS ui2,
          MTP2
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED, '')))) <> 'Y'
          AND QTYMIN IS NOT NULL
          AND ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYMIN), ',', '')) = 1
          AND CONVERT(float, REPLACE(CONVERT(varchar(50), QTYMIN), ',', '')) >= 0
          AND ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) = 1
          AND CONVERT(float, REPLACE(CONVERT(varchar(50), QTYOH2), ',', ''))
              <= CONVERT(float, REPLACE(CONVERT(varchar(50), QTYMIN), ',', ''))
        ORDER BY BCODE
        """
    )
    out: dict[str, dict[str, Any]] = {}
    with engine.connect() as conn:
        rows = conn.execute(sql, {"lim": int(limit)}).mappings().all()
    for row in rows:
        bcode = (row["bcode"] or "").strip()
        if not bcode:
            continue
        qtyoh2 = _parse_qty(row["QTYOH2"])
        qtymin = _parse_qty(row["QTYMIN"])
        qtyget = _parse_qty(row["QTYGET"])
        suggest = qtyget if qtyget > 0 else max(qtymin - qtyoh2, 1.0)
        mtp2 = _parse_qty(row["MTP2"]) or 1.0
        out[bcode] = {
            "bcode": bcode,
            "descr": (row["descr"] or "").strip(),
            "model": (row["model"] or "").strip(),
            "suggest_qty": suggest,
            "qtyoh2": qtyoh2,
            "qtymin": qtymin,
            "ui1": (row["ui1"] or "").strip(),
            "ui2": (row["ui2"] or "").strip(),
            "mtp2": mtp2 if mtp2 > 0 else 1.0,
            "source": "icmas",
        }
    return out


def suggest_transfer_skus(*, site: str, limit: int = 200) -> list[dict[str, Any]]:
    """Suggest pick list for transfer request.

    SYP: ICLOW รอสั่งซื้อ (same as /po) + ICMAS low-stock extras.
    HQ: ICMAS low-stock only — HQ ICLOW is for supplier PO, not branch transfer.
    """
    site_key = (site or "hq").strip().lower()
    lim = max(1, min(int(limit or 200), 200))
    include_iclow = site_key != "hq"
    iclow_rows = _fetch_all_iclow_to_be_ordered(site_key) if include_iclow else []

    iclow_order: list[str] = []
    by_bcode: dict[str, dict[str, Any]] = {}
    for row in iclow_rows:
        bcode = (row.get("bcode") or "").strip()
        if not bcode:
            continue
        qty = _parse_qty(row.get("qty") or row.get("ordered_qty"))
        if bcode in by_bcode:
            by_bcode[bcode]["suggest_qty"] += qty
            by_bcode[bcode]["iclow_line_count"] = int(by_bcode[bcode].get("iclow_line_count") or 1) + 1
            continue
        iclow_order.append(bcode)
        by_bcode[bcode] = {
            "bcode": bcode,
            "descr": (row.get("descr") or "").strip(),
            "model": "",
            "suggest_qty": qty,
            "qtyoh2": 0.0,
            "hq_qtyoh2": 0.0,
            "syp_qtyoh2": 0.0,
            "qtymin": 0.0,
            "ui1": (row.get("ui") or "").strip(),
            "ui2": "",
            "mtp2": 1.0,
            "source": "iclow",
            "iclow_line_count": 1,
        }

    icmas_candidates = _suggest_from_icmas_low_stock(
        get_site_engine(site_key), limit=_ICMAS_EXTRA_LIMIT
    )
    icmas_bcodes = [b for b in icmas_candidates if b not in by_bcode]

    all_bcodes = list(dict.fromkeys([*iclow_order, *icmas_bcodes]))
    # Stock columns must show live QTYOH2 even for do-not-restock (QTYMIN<0) SKUs.
    hq_icmas, syp_icmas = _fetch_dual_icmas(all_bcodes, include_blocked=True)
    local_icmas = hq_icmas if site_key == "hq" else syp_icmas

    out: list[dict[str, Any]] = []
    for bcode in iclow_order:
        if len(out) >= lim:
            break
        local_meta = local_icmas.get(bcode)
        if local_meta and local_meta.get("blocked"):
            continue
        item = dict(by_bcode[bcode])
        out.append(_enrich_suggest_item(item, site_key=site_key, hq_icmas=hq_icmas, syp_icmas=syp_icmas))

    for bcode in sorted(icmas_bcodes):
        if len(out) >= lim + _ICMAS_EXTRA_LIMIT:
            break
        row = icmas_candidates[bcode]
        local_meta = local_icmas.get(bcode)
        if local_meta and local_meta.get("blocked"):
            continue
        item = {
            "bcode": bcode,
            "descr": row.get("descr") or "",
            "model": row.get("model") or "",
            "suggest_qty": row.get("suggest_qty") or 1.0,
            "qtyoh2": row.get("qtyoh2") or 0.0,
            "hq_qtyoh2": 0.0,
            "syp_qtyoh2": 0.0,
            "qtymin": row.get("qtymin") or 0.0,
            "ui1": row.get("ui1") or "",
            "ui2": row.get("ui2") or "",
            "mtp2": row.get("mtp2") or 1.0,
            "source": "icmas",
            "iclow_line_count": 0,
        }
        out.append(_enrich_suggest_item(item, site_key=site_key, hq_icmas=hq_icmas, syp_icmas=syp_icmas))

    return out


def lookup_transfer_product(*, bcode: str) -> dict[str, Any] | None:
    """Resolve BCODE to ICMAS display fields (HQ + SYP stock)."""
    code = (bcode or "").strip()
    if not code:
        return None
    hq_icmas, syp_icmas = _fetch_dual_icmas([code], include_blocked=True)
    hq_meta = hq_icmas.get(code)
    syp_meta = syp_icmas.get(code)
    if not hq_meta and not syp_meta:
        return None
    descr = ""
    model = ""
    ui1 = ""
    ui2 = ""
    mtp2 = 1.0
    for meta in (syp_meta, hq_meta):
        if not meta:
            continue
        if not descr and meta.get("descr"):
            descr = meta["descr"]
        if not model and meta.get("model"):
            model = meta["model"]
        if not ui1 and meta.get("ui1"):
            ui1 = meta["ui1"]
        if not ui2 and meta.get("ui2"):
            ui2 = meta["ui2"]
        if float(meta.get("mtp2") or 1.0) > 1.0:
            mtp2 = float(meta["mtp2"])
    blocked = bool((hq_meta or {}).get("blocked") or (syp_meta or {}).get("blocked"))
    location_hq = ((hq_meta or {}).get("location") or "").strip()
    location_syp = ((syp_meta or {}).get("location") or "").strip()
    return {
        "bcode": code,
        "descr": descr,
        "model": model,
        "hq_qtyoh2": float((hq_meta or {}).get("qtyoh2") or 0),
        "syp_qtyoh2": float((syp_meta or {}).get("qtyoh2") or 0),
        "hq_qtymin": float((hq_meta or {}).get("qtymin") or 0) if hq_meta else None,
        "hq_no_stock": bool((hq_meta or {}).get("blocked")),
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
        "do_not_restock": blocked,
        "location_hq": location_hq,
        "location_syp": location_syp,
        "location": location_hq or location_syp,
        "location1": ((hq_meta or syp_meta or {}).get("location1") or "").strip(),
        "location2": ((hq_meta or syp_meta or {}).get("location2") or "").strip(),
    }


def enrich_transfer_lines(
    lines: list[dict[str, Any]],
    *,
    from_branch: str | None = None,
    to_branch: str | None = None,
) -> list[dict[str, Any]]:
    """Fill descr and live ICMAS stock (QTYOH2) from PARTS9 for transfer line dicts."""
    codes = sorted({(ln.get("bcode") or "").strip() for ln in lines if (ln.get("bcode") or "").strip()})
    if not codes:
        return [dict(ln) for ln in lines]
    hq_icmas, syp_icmas = _fetch_dual_icmas(codes, include_blocked=True)
    from_u = (from_branch or "").strip().upper()
    to_u = (to_branch or "").strip().upper()
    out: list[dict[str, Any]] = []
    for ln in lines:
        row = dict(ln)
        bcode = (row.get("bcode") or "").strip()
        if not bcode:
            out.append(row)
            continue
        hq_meta = hq_icmas.get(bcode) or {}
        syp_meta = syp_icmas.get(bcode) or {}
        row["hq_qtyoh2"] = float(hq_meta.get("qtyoh2") or 0)
        row["syp_qtyoh2"] = float(syp_meta.get("qtyoh2") or 0)
        row["hq_qtymin"] = float(hq_meta["qtymin"]) if hq_meta and "qtymin" in hq_meta else None
        row["hq_no_stock"] = bool(hq_meta.get("blocked"))
        row["location_hq"] = (hq_meta.get("location") or "").strip()
        row["location_syp"] = (syp_meta.get("location") or "").strip()
        if from_u == "HQ":
            row["from_qtyoh2"] = row["hq_qtyoh2"]
            row["location"] = row["location_hq"]
            row["location1"] = (hq_meta.get("location1") or "").strip()
            row["location2"] = (hq_meta.get("location2") or "").strip()
        elif from_u == "SYP":
            row["from_qtyoh2"] = row["syp_qtyoh2"]
            row["location"] = row["location_syp"]
            row["location1"] = (syp_meta.get("location1") or "").strip()
            row["location2"] = (syp_meta.get("location2") or "").strip()
        else:
            row["location"] = row["location_hq"] or row["location_syp"]
            prefer = hq_meta or syp_meta
            row["location1"] = (prefer.get("location1") or "").strip()
            row["location2"] = (prefer.get("location2") or "").strip()
        if to_u == "HQ":
            row["to_qtyoh2"] = row["hq_qtyoh2"]
        elif to_u == "SYP":
            row["to_qtyoh2"] = row["syp_qtyoh2"]
        for meta in (hq_meta, syp_meta):
            if not meta:
                continue
            if not row.get("descr") and meta.get("descr"):
                row["descr"] = meta["descr"]
            if not row.get("model") and meta.get("model"):
                row["model"] = meta["model"]
            if not row.get("ui1") and meta.get("ui1"):
                row["ui1"] = meta["ui1"]
            if not row.get("ui2") and meta.get("ui2"):
                row["ui2"] = meta["ui2"]
            if float(meta.get("mtp2") or 1.0) > 1.0:
                row["mtp2"] = float(meta["mtp2"])
        out.append(row)
    return out


def fetch_sticker_catalog(bcodes: list[str], *, site: str | None = None) -> dict[str, dict[str, Any]]:
    """ICMAS fields for the 5×3.5 cm receive sticker, from the receiving site's PARTS9."""
    codes = sorted({(c or "").strip() for c in bcodes if (c or "").strip()})
    if not codes:
        return {}
    site_key = (site or get_transfer_settings().site or "hq").strip().lower()
    if site_key not in ("hq", "syp"):
        site_key = "hq"
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    sql = text(
        f"""
        SELECT
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR, ''))) AS descr,
          LTRIM(RTRIM(COALESCE(BRAND, ''))) AS brand,
          LTRIM(RTRIM(COALESCE(MODEL, ''))) AS model,
          LTRIM(RTRIM(COALESCE(ACODE, ''))) AS acode,
          LTRIM(RTRIM(COALESCE(UI1, ''))) AS ui1,
          LTRIM(RTRIM(COALESCE(LOCATION1, ''))) AS location1,
          LTRIM(RTRIM(COALESCE(LOCATION2, ''))) AS location2,
          LTRIM(RTRIM(COALESCE(MCODE, ''))) AS mcode,
          LTRIM(RTRIM(COALESCE(PCODE, ''))) AS pcode,
          LTRIM(RTRIM(COALESCE(VENDOR, ''))) AS vendor,
          COSTNET,
          PRICE1
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})
        """
    )
    out: dict[str, dict[str, Any]] = {}
    try:
        engine = get_site_engine(site_key)
        with engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("sticker ICMAS fetch failed (%s): %s", site_key, exc)
        return {}
    for row in rows:
        bcode = (row.get("bcode") or "").strip()
        if not bcode:
            continue
        out[bcode] = {
            "bcode": bcode,
            "descr": (row.get("descr") or "").strip(),
            "brand": (row.get("brand") or "").strip(),
            "model": (row.get("model") or "").strip(),
            "acode": (row.get("acode") or "").strip(),
            "ui1": (row.get("ui1") or "").strip(),
            "location1": (row.get("location1") or "").strip(),
            "location2": (row.get("location2") or "").strip(),
            "mcode": (row.get("mcode") or "").strip(),
            "pcode": (row.get("pcode") or "").strip(),
            "vendor": (row.get("vendor") or "").strip(),
            "costnet": row.get("COSTNET"),
            "price1": row.get("PRICE1"),
        }
    return out
