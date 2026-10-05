"""Cost figures in the explorer are visible to LINE access_group admin only."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_INSIGHT_COST_KEYS = frozenset(
    {
        "margin",
        "price_margin",
        "avg_buy",
        "avg_buy_12m",
        "avg_buy_prior_12m",
        "last_buy_price",
        "avg_price",
        "list_pct",
        "realized_pct_12m",
        "realized_pct_prior_12m",
        "margin_pct",
        "margin_pct_list",
        "margin_pct_12m",
        "margin_pct_prior_12m",
        "margin_delta_pp",
        "margin_flag",
        "margin_trend",
        "cost_change_pct_12m",
        "buy_cost_change_pct_12m",
        "COSTAVG",
        "COSTLAST",
        "costavg",
        "costlast",
    }
)
_LINE_COST_KEYS = frozenset(
    {"FIFO_UNIT", "FIFO_EXT", "FIFO_STATUS", "MARGIN", "VS_LAST", "VS_AVG", "PRICE", "AMOUNT"}
)
_PURCHASE_KINDS = frozenset({"pi", "po", "iclow"})
_PURCHASE_MONEY = frozenset({"PRICE", "AMOUNT", "AFTERTAX"})


def can_see_explorer_cost(line_user_id: str | None) -> bool:
    uid = (line_user_id or "").strip()
    if not uid or uid == "tailscale":
        return False
    try:
        from src.access.helper import get_line_access
        from src.db.engine import get_engine

        access = get_line_access(get_engine(), uid)
    except Exception:
        log.exception("explorer cost access lookup failed")
        return False
    group = ((access or {}).get("access_group") or "").strip().lower()
    return group == "admin"


def redact_insight(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    return _drop_keys(payload)


def redact_movement(movement: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(movement or {})
    data["pi"] = [_without(row, _PURCHASE_MONEY) for row in data.get("pi") or []]
    data["sales"] = [_without(row, _LINE_COST_KEYS - {"PRICE", "AMOUNT"}) for row in data.get("sales") or []]
    return data


def redact_documents(documents: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [_redact_doc(doc) for doc in documents or []]


def redact_iclow_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(summary, dict):
        return summary
    out = dict(summary)
    totals = dict(out.get("totals") or {})
    totals.pop("pending_amount", None)
    out["totals"] = totals
    out["vendors"] = [_without(row, {"amount"}) for row in out.get("vendors") or []]
    out["recent_pending"] = [_without(row, _PURCHASE_MONEY) for row in out.get("recent_pending") or []]
    return out


def redact_ap(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    out = _drop_keys(payload)
    lines = []
    for row in out.get("iclow_lines") or []:
        lines.append(_without(row, {"amount"}))
    out["iclow_lines"] = lines
    return out


def _redact_doc(doc: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, dict):
        return doc
    out = dict(doc)
    kind = str(doc.get("kind") or "").lower()
    if kind in _PURCHASE_KINDS:
        out["header"] = _without(doc.get("header") or {}, _PURCHASE_MONEY)
        out["lines"] = [_without(row, _PURCHASE_MONEY) for row in doc.get("lines") or []]
    iclow = doc.get("iclow")
    if isinstance(iclow, dict):
        block = dict(iclow)
        block["lines"] = [_without(row, _PURCHASE_MONEY) for row in iclow.get("lines") or []]
        out["iclow"] = block
    if doc.get("bills"):
        out["bills"] = [_redact_doc(bill) for bill in doc["bills"]]
    return out


def _drop_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_keys(item) for key, item in value.items() if key not in _INSIGHT_COST_KEYS}
    if isinstance(value, list):
        return [_drop_keys(item) for item in value]
    return value


def _without(row: dict[str, Any], keys: set[str] | frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in dict(row).items() if key not in keys}
