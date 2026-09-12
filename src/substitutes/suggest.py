"""Live substitute suggestions (not catalog).

Signals (suggestion only — never gates ส่งแทน):
  - remarks: directed REMARKS “use BCODE instead”
  - code_size: same CODE1 + exact SIZE1/2/3
  - pcode: same OEM / เบอร์แท้
  - mcode: same factory / เบอร์โรงงาน
"""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from sqlalchemy import text

from src.parts9_explorer.db import get_site_engine
from src.substitutes.enrich import EngineFactory, enrich_member_rows

logger = logging.getLogger(__name__)

SOURCE_PRIORITY = {"remarks": 0, "code_size": 1, "pcode": 2, "mcode": 3}
SOURCE_LABELS = {
    "remarks": "REMARKS",
    "code_size": "รหัส+ขนาด",
    "pcode": "PCODE",
    "mcode": "MCODE",
}

_PEER_CAP = 8
_SUGGEST_WORKERS = 6
_SUGGEST_CACHE_TTL_SEC = 45.0
_suggest_cache: dict[tuple[str, str, int], tuple[float, list[dict[str, Any]]]] = {}
_suggest_cache_lock = threading.Lock()

STRONG_LINK_RE = re.compile(
    r"(?:ใช้รหัส|ใช่รหัส|ใช้\s*รหัส|รหัส)\s*[:=]?\s*(\d{8})\s*แทน"
    r"|ใช้\s*(\d{8})\s*แทน"
    r"|ใช้แทน[^\d]{0,20}(\d{8})"
    r"|(\d{8})\s*ใช้รหัสนี้แทน"
    r"|ใช้รหัสแทน\s*(\d{8})"
    r"|แทนได้[^\d]{0,10}(\d{8})"
    r"|(\d{8})\s*ใช้รหัสนี้แทนได้"
    r"|ใช้\s*รหัส\s*(\d{8})",
    re.I,
)

_DIRTY_PN = re.compile(r"ราคา|ซม|มม|มิล|ปี|บาท|เดือน", re.I)
_THAI = re.compile(r"[ก-๙]")

FetchSourceFn = Callable[[str], dict[str, Any] | None]
FindPeersFn = Callable[..., list[dict[str, Any]]]


def is_clean_part_number(code: str) -> bool:
    """True for usable PCODE/MCODE values (ICMAS dict §4 + Phase 0 filters)."""
    c = (code or "").strip()
    if not c or len(c) < 5 or len(c) > 36:
        return False
    if _THAI.search(c):
        return False
    if _DIRTY_PN.search(c):
        return False
    return True


def extract_remarks_peers(source_bcode: str, remarks: str) -> list[str]:
    """Directed peers from strong ‘use BCODE instead’ phrasing only."""
    peers: list[str] = []
    text_r = remarks or ""
    src = (source_bcode or "").strip()
    for m in STRONG_LINK_RE.finditer(text_r):
        for g in m.groups():
            if g and g != src and g not in peers:
                peers.append(g)
    for m in re.finditer(r"ใช้รหัส\s*(\d{8})\s*แทน|ใช่รหัส\s*(\d{8})\s*แทน", text_r):
        g = m.group(1) or m.group(2)
        if g and g != src and g not in peers:
            peers.append(g)
    if not peers:
        near = re.findall(r"(?:ใช้|รหัส|แทน)[^\d]{0,8}(\d{8})", text_r)
        near = [p for p in near if p != src]
        seen: set[str] = set()
        near_u: list[str] = []
        for p in near:
            if p not in seen:
                seen.add(p)
                near_u.append(p)
        if len(near_u) == 1:
            peers = near_u
    return peers


def _source_rank(source: str) -> int:
    return SOURCE_PRIORITY.get(source, 99)


def merge_suggestion_hits(
    hits: list[dict[str, Any]],
    *,
    cap: int = _PEER_CAP,
) -> list[dict[str, Any]]:
    """Union by bcode; primary source = highest priority; keep sources[]."""
    by: dict[str, dict[str, Any]] = {}
    for hit in hits:
        code = str(hit.get("bcode") or "").strip()
        if not code:
            continue
        src = str(hit.get("source") or "").strip() or "unknown"
        evid = (hit.get("evidence") or "").strip()
        cur = by.get(code)
        if not cur:
            by[code] = {
                "bcode": code,
                "source": src,
                "sources": [src],
                "evidence": evid,
                "descr": hit.get("descr") or "",
            }
            continue
        sources = list(cur.get("sources") or [])
        if src not in sources:
            sources.append(src)
        if _source_rank(src) < _source_rank(str(cur.get("source") or "")):
            cur["source"] = src
        if evid and evid not in (cur.get("evidence") or ""):
            cur["evidence"] = (
                f"{cur['evidence']}; {evid}" if cur.get("evidence") else evid
            )
        cur["sources"] = sorted(sources, key=_source_rank)
        if hit.get("descr") and not cur.get("descr"):
            cur["descr"] = hit["descr"]
    out = list(by.values())
    out.sort(key=lambda r: (_source_rank(str(r.get("source") or "")), str(r.get("bcode") or "")))
    return out[: max(1, int(cap))]


def _fetch_hq_source_row(
    bcode: str,
    *,
    get_engine: EngineFactory = get_site_engine,
) -> dict[str, Any] | None:
    code = (bcode or "").strip()
    if not code:
        return None
    try:
        engine = get_engine("hq")
    except Exception:
        return None
    # REMARKS is ntext on HQ ICMAS — RTRIM/COALESCE on ntext raises 8116.
    sql = text(
        """
        SELECT TOP 1
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(DESCR, '')))) AS descr,
          LTRIM(RTRIM(CONVERT(nvarchar(4000), COALESCE(CONVERT(nvarchar(4000), REMARKS), N'')))) AS remarks,
          UPPER(LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(CODE1, ''))))) AS code1,
          LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE1), ''))) AS size1,
          LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE2), ''))) AS size2,
          LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE3), ''))) AS size3,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE, '')))) AS pcode,
          LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE, '')))) AS mcode
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
        """
    )
    try:
        with engine.connect() as conn:
            row = conn.execute(sql, {"bcode": code}).mappings().first()
    except Exception as exc:  # noqa: BLE001
        logger.warning("suggest source fetch failed for %s: %s", code, exc)
        return None
    if not row:
        return None
    return {k: (row.get(k) or "") for k in (
        "bcode", "descr", "remarks", "code1", "size1", "size2", "size3", "pcode", "mcode"
    )}


def _size_exact_sql(slot: int, key: str) -> str:
    return f"LTRIM(RTRIM(COALESCE(CONVERT(varchar(40), SIZE{slot}), ''))) = :{key}"


def _find_code_size_peers(
    *,
    source_bcode: str,
    code1: str,
    size1: str,
    size2: str,
    size3: str,
    get_engine: EngineFactory = get_site_engine,
    limit: int = _PEER_CAP,
) -> list[dict[str, Any]]:
    c1 = (code1 or "").strip().upper()
    if not c1:
        return []
    s1, s2, s3 = (size1 or "").strip(), (size2 or "").strip(), (size3 or "").strip()
    if not (s1 or s2 or s3):
        return []
    try:
        engine = get_engine("hq")
    except Exception:
        return []
    where = [
        "LTRIM(RTRIM(BCODE)) <> :src",
        "UPPER(LTRIM(RTRIM(COALESCE(CODE1,'')))) = :code1",
    ]
    params: dict[str, Any] = {"src": source_bcode.strip(), "code1": c1, "lim": int(limit)}
    for slot, val, key in ((1, s1, "sz1"), (2, s2, "sz2"), (3, s3, "sz3")):
        if val:
            where.append(_size_exact_sql(slot, key))
            params[key] = val
    sql = text(
        f"""
        SELECT TOP (:lim)
          LTRIM(RTRIM(BCODE)) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR,''))) AS descr
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE {" AND ".join(where)}
        ORDER BY BCODE
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("code_size peer query failed: %s", exc)
        return []
    evid = f"CODE1={c1} SIZE={s1 or '-'}×{s2 or '-'}×{s3 or '-'}"
    return [
        {
            "bcode": str(r["bcode"]).strip(),
            "descr": str(r.get("descr") or "").strip(),
            "source": "code_size",
            "evidence": evid,
        }
        for r in rows
        if str(r.get("bcode") or "").strip()
    ]


def _find_cross_code_peers(
    *,
    source_bcode: str,
    field: str,
    value: str,
    source_tag: str,
    get_engine: EngineFactory = get_site_engine,
    limit: int = _PEER_CAP,
) -> list[dict[str, Any]]:
    assert field in ("PCODE", "MCODE")
    val = (value or "").strip()
    if not is_clean_part_number(val):
        return []
    try:
        engine = get_engine("hq")
    except Exception:
        return []
    sql = text(
        f"""
        SELECT TOP (:lim)
          LTRIM(RTRIM(BCODE)) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR,''))) AS descr
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(BCODE)) <> :src
          AND LTRIM(RTRIM(COALESCE({field},''))) = :val
        ORDER BY BCODE
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql, {"src": source_bcode.strip(), "val": val, "lim": int(limit)}
            ).mappings().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s peer query failed: %s", field, exc)
        return []
    return [
        {
            "bcode": str(r["bcode"]).strip(),
            "descr": str(r.get("descr") or "").strip(),
            "source": source_tag,
            "evidence": f"{field}={val}",
        }
        for r in rows
        if str(r.get("bcode") or "").strip()
    ]


def collect_suggestion_hits(
    source: dict[str, Any],
    *,
    find_code_size: FindPeersFn | None = None,
    find_pcode: FindPeersFn | None = None,
    find_mcode: FindPeersFn | None = None,
    get_engine: EngineFactory = get_site_engine,
    cap: int = _PEER_CAP,
) -> list[dict[str, Any]]:
    """Run all live signals for one source row (no stock enrich yet)."""
    bcode = str(source.get("bcode") or "").strip()
    if not bcode:
        return []
    hits: list[dict[str, Any]] = []

    for peer in extract_remarks_peers(bcode, str(source.get("remarks") or "")):
        hits.append(
            {
                "bcode": peer,
                "source": "remarks",
                "evidence": f"REMARKS→{peer}",
            }
        )

    cs_fn = find_code_size or (
        lambda **kw: _find_code_size_peers(get_engine=get_engine, limit=cap, **kw)
    )
    hits.extend(
        cs_fn(
            source_bcode=bcode,
            code1=str(source.get("code1") or ""),
            size1=str(source.get("size1") or ""),
            size2=str(source.get("size2") or ""),
            size3=str(source.get("size3") or ""),
        )
    )

    pc_fn = find_pcode or (
        lambda **kw: _find_cross_code_peers(
            field="PCODE", source_tag="pcode", get_engine=get_engine, limit=cap, **kw
        )
    )
    hits.extend(
        pc_fn(source_bcode=bcode, value=str(source.get("pcode") or ""))
    )

    mc_fn = find_mcode or (
        lambda **kw: _find_cross_code_peers(
            field="MCODE", source_tag="mcode", get_engine=get_engine, limit=cap, **kw
        )
    )
    hits.extend(
        mc_fn(source_bcode=bcode, value=str(source.get("mcode") or ""))
    )

    return merge_suggestion_hits(
        [h for h in hits if str(h.get("bcode") or "").strip() != bcode],
        cap=cap,
    )


def suggest_for_bcode(
    bcode: str,
    *,
    fetch_source: FetchSourceFn | None = None,
    find_code_size: FindPeersFn | None = None,
    find_pcode: FindPeersFn | None = None,
    find_mcode: FindPeersFn | None = None,
    get_engine: EngineFactory = get_site_engine,
    ship_branch: str | None = None,
    cap: int = _PEER_CAP,
) -> list[dict[str, Any]]:
    """Live suggestions for one BCODE (enriched dual stock)."""
    code = (bcode or "").strip()
    if not code:
        return []
    src_fn = fetch_source or (lambda b: _fetch_hq_source_row(b, get_engine=get_engine))
    source = src_fn(code)
    if not source:
        return []
    merged = collect_suggestion_hits(
        source,
        find_code_size=find_code_size,
        find_pcode=find_pcode,
        find_mcode=find_mcode,
        get_engine=get_engine,
        cap=cap,
    )
    if not merged:
        return []
    enriched = enrich_member_rows(merged, get_engine=get_engine)
    branch = (ship_branch or "").strip().upper()

    def stock_key(row: dict[str, Any]) -> tuple:
        if branch == "HQ":
            q = row.get("hq_qtyoh2")
        elif branch == "SYP":
            q = row.get("syp_qtyoh2")
        else:
            q = row.get("hq_qtyoh2")
        try:
            stock = float(q) if q is not None else -1.0
        except (TypeError, ValueError):
            stock = -1.0
        return (-stock, _source_rank(str(row.get("source") or "")), str(row.get("bcode") or ""))

    enriched.sort(key=stock_key)
    out: list[dict[str, Any]] = []
    for row in enriched[:cap]:
        out.append(
            {
                "bcode": row.get("bcode"),
                "descr": row.get("descr") or "",
                "hq_qtyoh2": row.get("hq_qtyoh2"),
                "hq_qtymin": row.get("hq_qtymin"),
                "syp_qtyoh2": row.get("syp_qtyoh2"),
                "syp_qtymin": row.get("syp_qtymin"),
                "hq_l1": row.get("hq_l1"),
                "syp_l1": row.get("syp_l1"),
                "source": row.get("source"),
                "sources": row.get("sources") or [row.get("source")],
                "evidence": row.get("evidence") or "",
                "source_label": SOURCE_LABELS.get(str(row.get("source") or ""), str(row.get("source") or "")),
            }
        )
    return out


def _cache_get(key: tuple[str, str, int]) -> list[dict[str, Any]] | None:
    now = time.monotonic()
    with _suggest_cache_lock:
        hit = _suggest_cache.get(key)
        if not hit:
            return None
        ts, payload = hit
        if (now - ts) > _SUGGEST_CACHE_TTL_SEC:
            _suggest_cache.pop(key, None)
            return None
        return [dict(row) for row in payload]


def _cache_put(key: tuple[str, str, int], rows: list[dict[str, Any]]) -> None:
    with _suggest_cache_lock:
        _suggest_cache[key] = (time.monotonic(), [dict(row) for row in rows])
        if len(_suggest_cache) > 256:
            oldest = sorted(_suggest_cache.items(), key=lambda kv: kv[1][0])[:64]
            for k, _ in oldest:
                _suggest_cache.pop(k, None)


def suggest_for_bcodes(
    bcodes: list[str],
    *,
    fetch_source: FetchSourceFn | None = None,
    find_code_size: FindPeersFn | None = None,
    find_pcode: FindPeersFn | None = None,
    find_mcode: FindPeersFn | None = None,
    get_engine: EngineFactory = get_site_engine,
    ship_branch: str | None = None,
    cap: int = _PEER_CAP,
) -> dict[str, list[dict[str, Any]]]:
    """Map bcode → live suggestion list (parallel + short TTL cache)."""
    branch = (ship_branch or "").strip().upper()
    codes: list[str] = []
    seen: set[str] = set()
    for raw in bcodes:
        code = (raw or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)

    out: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for code in codes:
        cached = _cache_get((code, branch, int(cap)))
        if cached is not None:
            out[code] = cached
        else:
            missing.append(code)

    def _one(code: str) -> tuple[str, list[dict[str, Any]]]:
        try:
            rows = suggest_for_bcode(
                code,
                fetch_source=fetch_source,
                find_code_size=find_code_size,
                find_pcode=find_pcode,
                find_mcode=find_mcode,
                get_engine=get_engine,
                ship_branch=ship_branch,
                cap=cap,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("suggest_for_bcode %s failed: %s", code, exc)
            rows = []
        _cache_put((code, branch, int(cap)), rows)
        return code, rows

    if not missing:
        return out
    if len(missing) == 1:
        code, rows = _one(missing[0])
        out[code] = rows
        return out

    workers = min(_SUGGEST_WORKERS, len(missing))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_one, code) for code in missing]
        for fut in as_completed(futs):
            code, rows = fut.result()
            out[code] = rows
    return out
