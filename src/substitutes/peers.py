"""Transfer-facing substitute hints — live suggestions (not catalog).

Catalog groups remain for confirmed ส่งแทน only (see ship_as.py).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from src.parts9_explorer.db import get_site_engine
from src.substitutes.enrich import EngineFactory

logger = logging.getLogger(__name__)

SuggestMapFn = Callable[[list[str]], dict[str, list[dict[str, Any]]]]

# Bulk suggest lists can have dozens of L-1/weak rows; each live lookup hits ICMAS
# several times. Cap keeps /api/suggest snappy; prepare (small N) leaves uncapped.
DEFAULT_SUGGEST_HINT_CAP = 12


def needs_substitute_hint(
    row: dict[str, Any],
    *,
    ship_branch: str,
    need_qty: float | None,
) -> bool:
    """True when ship-from is L-1 (QTYMIN < 0) or stock below need_qty."""
    branch = (ship_branch or "").strip().upper()
    if branch == "HQ":
        if row.get("hq_no_stock") is True:
            return True
        qtymin = row.get("hq_qtymin")
        try:
            if qtymin is not None and float(qtymin) < 0:
                return True
        except (TypeError, ValueError):
            pass
        qtyoh2 = row.get("hq_qtyoh2")
    elif branch == "SYP":
        qtymin = row.get("syp_qtymin")
        try:
            if qtymin is not None and float(qtymin) < 0:
                return True
        except (TypeError, ValueError):
            pass
        qtyoh2 = row.get("syp_qtyoh2")
    else:
        return False
    if need_qty is None:
        return False
    try:
        need = float(need_qty)
        stock = float(qtyoh2) if qtyoh2 is not None else None
    except (TypeError, ValueError):
        return False
    if stock is None:
        return False
    return stock < need


def _hint_priority(
    row: dict[str, Any],
    *,
    ship_branch: str,
    need_qty: float | None,
) -> tuple:
    """Sort key: L-1 / blocked first, then largest stock deficit."""
    branch = (ship_branch or "").strip().upper()
    if branch == "HQ":
        blocked = bool(row.get("hq_no_stock"))
        try:
            l1 = blocked or (
                row.get("hq_qtymin") is not None and float(row.get("hq_qtymin")) < 0
            )
        except (TypeError, ValueError):
            l1 = blocked
        qtyoh2 = row.get("hq_qtyoh2")
    else:
        try:
            l1 = row.get("syp_qtymin") is not None and float(row.get("syp_qtymin")) < 0
        except (TypeError, ValueError):
            l1 = False
        qtyoh2 = row.get("syp_qtyoh2")
    try:
        need = float(need_qty) if need_qty is not None else 0.0
    except (TypeError, ValueError):
        need = 0.0
    try:
        stock = float(qtyoh2) if qtyoh2 is not None else 0.0
    except (TypeError, ValueError):
        stock = 0.0
    deficit = need - stock
    return (0 if l1 else 1, -deficit, str(row.get("bcode") or ""))


def _default_suggest_map(
    bcodes: list[str],
    *,
    ship_branch: str,
    get_engine: EngineFactory,
) -> dict[str, list[dict[str, Any]]]:
    from src.substitutes.suggest import suggest_for_bcodes

    return suggest_for_bcodes(
        bcodes, get_engine=get_engine, ship_branch=ship_branch
    )


def attach_live_suggestions(
    items: list[dict[str, Any]],
    *,
    ship_branch: str,
    need_qty_for: Callable[[dict[str, Any]], float | None],
    suggest_map_fn: SuggestMapFn | None = None,
    get_engine: EngineFactory = get_site_engine,
    max_codes: int | None = None,
) -> list[dict[str, Any]]:
    """Attach ``suggestions`` (and compat ``substitutes``) from live ICMAS signals.

    Catalog is not consulted. Failures are swallowed so transfer keeps working.
    ``max_codes`` limits how many SKUs get live lookups (bulk suggest path).
    """
    if not items:
        return items
    out = [dict(it) for it in items]
    for row in out:
        row.setdefault("suggestions", [])
        row.setdefault("substitutes", [])

    candidates: list[dict[str, Any]] = []
    for row in out:
        code = str(row.get("bcode") or "").strip()
        if not code:
            continue
        need = need_qty_for(row)
        if needs_substitute_hint(row, ship_branch=ship_branch, need_qty=need):
            candidates.append(row)
    if not candidates:
        return out

    candidates.sort(
        key=lambda r: _hint_priority(
            r, ship_branch=ship_branch, need_qty=need_qty_for(r)
        )
    )
    if max_codes is not None and max_codes >= 0:
        candidates = candidates[: max(0, int(max_codes))]
    need_codes = [str(r.get("bcode") or "").strip() for r in candidates]
    need_codes = [c for c in need_codes if c]
    if not need_codes:
        return out

    try:
        if suggest_map_fn is not None:
            peer_map = suggest_map_fn(need_codes) or {}
        else:
            peer_map = _default_suggest_map(
                need_codes, ship_branch=ship_branch, get_engine=get_engine
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("live substitute suggest skipped: %s", exc)
        return out

    allowed = set(need_codes)
    for row in out:
        code = str(row.get("bcode") or "").strip()
        if code in allowed and code in peer_map and needs_substitute_hint(
            row, ship_branch=ship_branch, need_qty=need_qty_for(row)
        ):
            peers = peer_map.get(code) or []
            row["suggestions"] = peers
            # Compat for existing UI that reads substitutes[]
            row["substitutes"] = peers
        else:
            row["suggestions"] = []
            row["substitutes"] = []
    return out


# Back-compat alias used by older call sites / tests
def attach_substitute_hints(
    items: list[dict[str, Any]],
    *,
    ship_branch: str,
    need_qty_for: Callable[[dict[str, Any]], float | None],
    bulk_peers_fn: Any = None,
    suggest_map_fn: SuggestMapFn | None = None,
    get_engine: EngineFactory = get_site_engine,
) -> list[dict[str, Any]]:
    """Attach live suggestions. ``bulk_peers_fn`` ignored (catalog is not used for hints)."""
    _ = bulk_peers_fn
    return attach_live_suggestions(
        items,
        ship_branch=ship_branch,
        need_qty_for=need_qty_for,
        suggest_map_fn=suggest_map_fn,
        get_engine=get_engine,
    )
