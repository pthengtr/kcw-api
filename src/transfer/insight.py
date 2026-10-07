"""HQ→SYP transfer recommendations from Supabase product insight.

Insight is a standing policy. The quantity shown here is the live gap versus
that policy, not the stored typical batch and not snapshot on-hand.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

INSIGHT_SITE = "hq"
FRESH_DAYS = 21
AI_ONLY_LIMIT = 200
_POLICY_TTL_SEC = 300.0

_policy_lock = threading.Lock()
_policy_cache: tuple[float, list[dict[str, Any]]] | None = None


def pack_gap(gap: float, mtp2: float | None) -> float:
    """Round a small-unit gap up to whole packs. MTP2 <= 1 rounds to a whole unit."""
    if gap <= 0:
        return 0.0
    mtp = float(mtp2) if mtp2 and float(mtp2) > 1 else 1.0
    packs = int(math.ceil(gap / mtp - 1e-9))
    return float(packs * mtp)


def parse_generated_at(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_fresh(generated_at: Any, *, now: datetime | None = None, days: int = FRESH_DAYS) -> bool:
    parsed = parse_generated_at(generated_at)
    if parsed is None:
        return False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current - timedelta(days=days) <= parsed <= current + timedelta(days=1)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _qty_text(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def policy_target(row: dict[str, Any]) -> float | None:
    """SYP holding target. Snapshot on-hand is not a target."""
    holding = _num(row.get("syp_safe_holding"))
    if holding is not None and holding > 0:
        return holding
    typical = _num(row.get("rec_transfer_qty_to_syp"))
    if typical is not None and typical > 0:
        return typical
    return None


def ai_recommendation(
    row: dict[str, Any],
    *,
    live_syp: float,
    live_hq: float,
    syp_blocked: bool,
    mtp2: float | None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Live HQ→SYP gap for one insight row. None when it should not be shown."""
    if syp_blocked or live_hq <= 0:
        return None
    if str(row.get("dead_stock") or "").strip().lower() == "yes":
        return None
    if not is_fresh(row.get("generated_at"), now=now):
        return None
    target = policy_target(row)
    # A sub-unit target is not a transfer. pack_gap would round 0.xx up to 1
    # (or a full carton), which filled the pick list with slow movers.
    if target is None or target < 1 or live_syp >= target:
        return None
    gap = target - live_syp
    packed = pack_gap(gap, mtp2)
    ai_qty = min(packed, live_hq)
    if ai_qty <= 0:
        return None
    monthly = _num(row.get("syp_monthly")) or 0.0
    reason = f"สาขา {_qty_text(live_syp)} / เป้า {_qty_text(target)}"
    extra = str(row.get("rec_transfer_reason") or "").strip()
    if extra:
        reason = f"{reason} · {extra[:160]}"
    return {
        "ai_qty": ai_qty,
        "generated_at": str(row.get("generated_at") or ""),
        "reason": reason,
        "target": target,
        "gap": gap,
        "monthly": monthly,
    }


def propose_meta_from_advice(advice: dict[str, Any], *, source: str) -> dict[str, Any]:
    return {
        "source": source,
        "reason": advice.get("reason") or "",
        "ai_qty": advice.get("ai_qty"),
        "generated_at": advice.get("generated_at") or "",
    }


def clean_propose_meta(raw: Any) -> dict[str, Any] | None:
    """Keep only the fields the pick list is allowed to store on a line."""
    if not isinstance(raw, dict):
        return None
    source = str(raw.get("source") or "").strip().lower()
    if source not in ("insight", "both"):
        return None
    ai_qty = _num(raw.get("ai_qty"))
    if ai_qty is None or ai_qty <= 0:
        return None
    generated = str(raw.get("generated_at") or "").strip()[:40]
    reason = str(raw.get("reason") or "").strip()[:300]
    return {
        "source": source,
        "reason": reason,
        "ai_qty": ai_qty,
        "generated_at": generated or None,
    }


def annotate_iclow_items(
    items: list[dict[str, Any]],
    policies: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
) -> None:
    """Attach an AI qty beside an existing ICLOW line. Does not change suggest_qty."""
    for item in items:
        if (item.get("source") or "") != "iclow":
            continue
        policy = policies.get((item.get("bcode") or "").strip())
        if not policy:
            continue
        syp_qty = _num(item.get("syp_qtyoh2"))
        hq_qty = _num(item.get("hq_qtyoh2"))
        if syp_qty is None or hq_qty is None:
            continue
        qtymin = _num(item.get("qtymin"))
        advice = ai_recommendation(
            policy,
            live_syp=syp_qty,
            live_hq=hq_qty,
            syp_blocked=qtymin is not None and qtymin < 0,
            mtp2=_num(item.get("mtp2")),
            now=now,
        )
        if not advice:
            continue
        item["propose_meta"] = propose_meta_from_advice(advice, source="both")


def build_insight_only_item(
    policy: dict[str, Any],
    advice: dict[str, Any],
    *,
    hq_meta: dict[str, Any],
    syp_meta: dict[str, Any],
) -> dict[str, Any]:
    descr = (syp_meta.get("descr") or hq_meta.get("descr") or "").strip()
    mtp2 = _num(syp_meta.get("mtp2")) or _num(hq_meta.get("mtp2")) or 1.0
    if mtp2 <= 0:
        mtp2 = 1.0
    ui1 = (syp_meta.get("ui1") or hq_meta.get("ui1") or "").strip()
    ui2 = (syp_meta.get("ui2") or hq_meta.get("ui2") or "").strip()
    syp_qty = _num(syp_meta.get("qtyoh2")) or 0.0
    return {
        "bcode": (policy.get("bcode") or "").strip(),
        "descr": descr,
        "model": (syp_meta.get("model") or hq_meta.get("model") or "").strip(),
        "brand": (syp_meta.get("brand") or hq_meta.get("brand") or "").strip(),
        "pcode": (syp_meta.get("pcode") or hq_meta.get("pcode") or "").strip(),
        "mcode": (syp_meta.get("mcode") or hq_meta.get("mcode") or "").strip(),
        "suggest_qty": advice["ai_qty"],
        "qtyoh2": syp_qty,
        "hq_qtyoh2": _num(hq_meta.get("qtyoh2")) or 0.0,
        "syp_qtyoh2": syp_qty,
        "qtymin": _num(syp_meta.get("qtymin")) or 0.0,
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
        "source": "insight",
        "iclow_line_count": 0,
        "location": (syp_meta.get("location") or "").strip(),
        "location_hq": (hq_meta.get("location") or "").strip(),
        "location_syp": (syp_meta.get("location") or "").strip(),
        "hq_qtymin": _num(hq_meta.get("qtymin")),
        "hq_no_stock": bool(hq_meta.get("blocked")),
        "suggestions": [],
        "substitutes": [],
        "propose_meta": propose_meta_from_advice(advice, source="insight"),
    }


def insight_only_lines(
    policies: dict[str, dict[str, Any]],
    *,
    iclow_bcodes: set[str],
    hq_icmas: dict[str, dict[str, Any]],
    syp_icmas: dict[str, dict[str, Any]],
    now: datetime | None = None,
    limit: int = AI_ONLY_LIMIT,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, float, str, dict[str, Any]]] = []
    for bcode, policy in policies.items():
        if bcode in iclow_bcodes:
            continue
        hq_meta = hq_icmas.get(bcode)
        syp_meta = syp_icmas.get(bcode)
        if not hq_meta or not syp_meta:
            continue
        mtp2 = _num(syp_meta.get("mtp2")) or _num(hq_meta.get("mtp2"))
        advice = ai_recommendation(
            policy,
            live_syp=_num(syp_meta.get("qtyoh2")) or 0.0,
            live_hq=_num(hq_meta.get("qtyoh2")) or 0.0,
            syp_blocked=bool(syp_meta.get("blocked")),
            mtp2=mtp2,
            now=now,
        )
        if not advice:
            continue
        ranked.append((
            float(advice["monthly"]),
            float(advice["gap"]),
            bcode,
            build_insight_only_item(policy, advice, hq_meta=hq_meta, syp_meta=syp_meta),
        ))
    # Demand first, then the live shortfall. Relative gap/monthly promoted
    # the slowest SKUs to the top of the list.
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return [row[3] for row in ranked[: max(0, limit)]]


def load_insight_policies() -> dict[str, dict[str, Any]]:
    """Postgres product_insight rows that can recommend an HQ→SYP transfer. Cached."""
    global _policy_cache
    now_m = time.monotonic()
    with _policy_lock:
        if _policy_cache and (now_m - _policy_cache[0]) <= _POLICY_TTL_SEC:
            return _policy_cache[1]
    rows = _fetch_insight_policies()
    with _policy_lock:
        _policy_cache = (time.monotonic(), rows)
    return rows


def clear_insight_policy_cache() -> None:
    global _policy_cache
    with _policy_lock:
        _policy_cache = None


def _fetch_insight_policies() -> dict[str, dict[str, Any]]:
    try:
        from src.db.engine import get_conn
    except Exception:
        logger.warning("product insight db import failed", exc_info=True)
        return {}
    sql = """
        SELECT
          btrim(bcode) AS bcode,
          generated_at,
          dead_stock,
          rec_transfer_qty_to_syp,
          rec_transfer_reason,
          NULLIF(insight_json #>> '{derived,transfer,syp_safe_holding}', '')::double precision
            AS syp_safe_holding,
          NULLIF(insight_json #>> '{derived,transfer,syp_monthly}', '')::double precision
            AS syp_monthly
        FROM product_insight.product_insights
        WHERE site = %s
          AND coalesce(dead_stock, '') <> 'yes'
          AND coalesce(rec_transfer_qty_to_syp, 0) > 0
    """
    out: dict[str, dict[str, Any]] = {}
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (INSIGHT_SITE,))
            cols = [d[0] for d in cur.description]
            for raw in cur.fetchall():
                row = dict(zip(cols, raw))
                bcode = str(row.get("bcode") or "").strip()
                if bcode:
                    out[bcode] = row
    except Exception:
        logger.warning("product insight policy read failed", exc_info=True)
        return {}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return out
