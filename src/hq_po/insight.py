"""Company safe-holding advice for the HQ PO list.

Same shape as transfer insight: a fresh policy, a live gap, pack rounding.
The target is company safe holding, and the live qty is HQ + SYP on-hand.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any

from src.transfer.insight import is_fresh, pack_gap

logger = logging.getLogger(__name__)

INSIGHT_SITE = "hq"
AI_ONLY_LIMIT = 200
_POLICY_TTL_SEC = 300.0

_policy_lock = threading.Lock()
_policy_cache: tuple[float, dict[str, dict[str, Any]]] | None = None


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
    """Company holding target. Snapshot on-hand is not a target."""
    holding = _num(row.get("safe_holding_qty"))
    if holding is not None and holding > 0:
        return holding
    typical = _num(row.get("suggested_order_qty"))
    if typical is not None and typical > 0:
        return typical
    return None


def ai_recommendation(
    row: dict[str, Any],
    *,
    live_company: float,
    mtp2: float | None,
    incoming: float = 0.0,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Live company gap versus safe holding. None when it should not be shown.

    incoming is ค้างรับ qty already ordered and not received. It covers the gap
    the same way on-hand does, so a product is not suggested again after confirm.
    """
    if str(row.get("dead_stock") or "").strip().lower() == "yes":
        return None
    if not is_fresh(row.get("generated_at"), now=now):
        return None
    held = incoming if incoming and incoming > 0 else 0.0
    covered = live_company + held
    target = policy_target(row)
    if target is None or target < 1 or covered >= target:
        return None
    gap = target - covered
    packed = pack_gap(gap, mtp2)
    if packed <= 0:
        return None
    reason = f"คงเหลือ {_qty_text(live_company)} / เป้า {_qty_text(target)}"
    if held > 0:
        reason = f"{reason} · ค้างรับ {_qty_text(held)}"
    extra = str(row.get("safe_holding_reason") or "").strip()
    if extra:
        reason = f"{reason} · {extra[:160]}"
    return {
        "ai_qty": packed,
        "generated_at": str(row.get("generated_at") or ""),
        "reason": reason,
        "target": target,
        "gap": gap,
    }


def propose_meta_from_advice(advice: dict[str, Any], *, source: str) -> dict[str, Any]:
    return {
        "source": source,
        "reason": advice.get("reason") or "",
        "ai_qty": advice.get("ai_qty"),
        "generated_at": advice.get("generated_at") or "",
    }


def clean_propose_meta(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    source = str(raw.get("source") or "").strip().lower()
    ai_qty = _num(raw.get("ai_qty"))
    parts9_qty = _num(raw.get("parts9_qty"))
    has_ai = ai_qty is not None and ai_qty > 0
    has_parts9 = parts9_qty is not None and parts9_qty > 0
    if source not in ("insight", "both", "parts9"):
        source = "insight" if has_ai else "parts9"
    if not has_ai and not has_parts9:
        return None
    out = {
        "source": source,
        "reason": str(raw.get("reason") or "").strip()[:300],
        "generated_at": str(raw.get("generated_at") or "").strip()[:40] or None,
    }
    if has_ai:
        out["ai_qty"] = ai_qty
    if has_parts9:
        out["parts9_qty"] = parts9_qty
    return out


def annotate_iclow_items(
    items: list[dict[str, Any]],
    policies: dict[str, dict[str, Any]],
    *,
    incoming: dict[str, float] | None = None,
    now: datetime | None = None,
) -> None:
    """Attach an AI qty beside an existing ICLOW line. Does not change qty."""
    held = incoming or {}
    for item in items:
        if item.get("source") != "iclow":
            continue
        if item.get("hq_blocked"):
            continue
        bcode = str(item.get("bcode") or "").strip()
        policy = policies.get(bcode)
        if not policy:
            continue
        hq_qty = _num(item.get("hq_qtyoh2"))
        syp_qty = _num(item.get("syp_qtyoh2"))
        if hq_qty is None or syp_qty is None:
            continue
        incoming_qty = float(held.get(bcode) or 0)
        item["incoming_qty"] = incoming_qty
        advice = ai_recommendation(
            policy,
            live_company=hq_qty + syp_qty,
            mtp2=_num(item.get("mtp2")),
            incoming=incoming_qty,
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
    vendor = str(policy.get("last_supplier") or "").strip()
    descr = (syp_meta.get("descr") or hq_meta.get("descr") or "").strip()
    mtp2 = _num(syp_meta.get("mtp2")) or _num(hq_meta.get("mtp2")) or 1.0
    if mtp2 <= 0:
        mtp2 = 1.0
    hq_qty = _num(hq_meta.get("qtyoh2")) or 0.0
    syp_qty = _num(syp_meta.get("qtyoh2")) or 0.0
    return {
        "iclow_id": None,
        "vendor": vendor,
        "vendor_name": None,
        "bcode": str(policy.get("bcode") or "").strip(),
        "descr": descr,
        "mcode": (hq_meta.get("mcode") or syp_meta.get("mcode") or "").strip(),
        "qty": advice["ai_qty"],
        "ui": (hq_meta.get("ui1") or syp_meta.get("ui1") or "").strip(),
        "source": "insight",
        "confirmable": bool(vendor) and float(advice["ai_qty"]) > 0,
        "incoming_qty": 0.0,
        "hq_qtyoh2": hq_qty,
        "syp_qtyoh2": syp_qty,
        "company_qtyoh2": hq_qty + syp_qty,
        "mtp2": mtp2,
        "hq_blocked": bool(hq_meta.get("blocked")),
        "propose_meta": propose_meta_from_advice(advice, source="insight"),
    }


def insight_only_lines(
    policies: dict[str, dict[str, Any]],
    *,
    iclow_bcodes: set[str],
    hq_icmas: dict[str, dict[str, Any]],
    syp_icmas: dict[str, dict[str, Any]],
    incoming: dict[str, float] | None = None,
    now: datetime | None = None,
    limit: int = AI_ONLY_LIMIT,
) -> list[dict[str, Any]]:
    held = incoming or {}
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for bcode, policy in policies.items():
        if bcode in iclow_bcodes:
            continue
        hq_meta = hq_icmas.get(bcode) or {"qtyoh2": 0, "blocked": False, "mtp2": 1}
        syp_meta = syp_icmas.get(bcode) or {"qtyoh2": 0, "blocked": False, "mtp2": 1}
        if bcode not in hq_icmas and bcode not in syp_icmas:
            continue
        if hq_meta.get("blocked"):
            continue
        incoming_qty = float(held.get(bcode) or 0)
        advice = ai_recommendation(
            policy,
            live_company=(_num(hq_meta.get("qtyoh2")) or 0.0) + (_num(syp_meta.get("qtyoh2")) or 0.0),
            mtp2=_num(hq_meta.get("mtp2")) or _num(syp_meta.get("mtp2")),
            incoming=incoming_qty,
            now=now,
        )
        if not advice:
            continue
        item = build_insight_only_item(policy, advice, hq_meta=hq_meta, syp_meta=syp_meta)
        item["incoming_qty"] = incoming_qty
        ranked.append((float(advice["gap"]), bcode, item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in ranked[: max(0, limit)]]


def load_insight_policies() -> dict[str, dict[str, Any]]:
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
          safe_holding_qty,
          safe_holding_reason,
          suggested_order_qty,
          last_supplier,
          rec_qtymin
        FROM product_insight.product_insights
        WHERE site = %s
          AND coalesce(dead_stock, '') <> 'yes'
          AND (
            coalesce(safe_holding_qty, 0) >= 1
            OR coalesce(suggested_order_qty, 0) >= 1
          )
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
        logger.warning("hq po insight policy read failed", exc_info=True)
        return {}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return out
