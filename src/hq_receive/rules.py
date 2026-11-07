"""Business rules for HQ vendor goods receipt.

AI may prefill; the operator must confirm before PARTS9 writes.
Writes stay HQ-only (KSS) and are gated by HQ_RECEIVE_PIMAS_WRITE_ENABLED.
"""

from __future__ import annotations

from typing import Any

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError

# Default tolerances when env not set (percent for cost; absolute units for qty).
DEFAULT_COST_TOLERANCE_PCT = 2.0
DEFAULT_QTY_TOLERANCE = 0.0001
DEFAULT_TOTAL_TOLERANCE = 1.0  # baht


def cost_tolerance_pct() -> float:
    settings = get_hq_receive_settings()
    return float(getattr(settings, "hq_receive_cost_tolerance_pct", DEFAULT_COST_TOLERANCE_PCT))


def qty_tolerance() -> float:
    settings = get_hq_receive_settings()
    return float(getattr(settings, "hq_receive_qty_tolerance", DEFAULT_QTY_TOLERANCE))


def total_tolerance() -> float:
    settings = get_hq_receive_settings()
    return float(getattr(settings, "hq_receive_total_tolerance", DEFAULT_TOTAL_TOLERANCE))


def cost_mismatch(expected: float | None, actual: float | None) -> bool:
    if expected is None or actual is None:
        return False
    exp = float(expected)
    act = float(actual)
    if exp <= 0:
        return act > 0
    pct = abs(act - exp) / exp * 100.0
    return pct > cost_tolerance_pct()


def qty_mismatch(ordered: float | None, received: float | None) -> bool:
    if ordered is None or received is None:
        return False
    return abs(float(ordered) - float(received)) > qty_tolerance()


def totals_mismatch(expected_net: float | None, computed_net: float | None) -> bool:
    if expected_net is None or computed_net is None:
        return False
    return abs(float(expected_net) - float(computed_net)) > total_tolerance()


def classify_line(
    *,
    open_qty: float | None,
    receive_qty: float,
    open_cost: float | None = None,
    receive_cost: float | None = None,
    known_product: bool = True,
) -> dict[str, Any]:
    """Return status + discrepancy kinds for one draft line before confirm."""
    flags: list[str] = []
    if not known_product:
        flags.append("unknown_product")
    if open_qty is not None and receive_qty > float(open_qty) + qty_tolerance():
        flags.append("over_po")
    elif open_qty is not None and receive_qty + qty_tolerance() < float(open_qty):
        # Partial receive is allowed — informational only.
        flags.append("under_po")
    if cost_mismatch(open_cost, receive_cost):
        flags.append("cost_mismatch")
    # Blockers: unknown product or receiving more than open ICLOW qty.
    # under_po / cost_mismatch warn but still confirmable (operator may accept).
    if "unknown_product" in flags or "over_po" in flags:
        status = "mismatch"
    elif "cost_mismatch" in flags:
        status = "ok"  # warning via flags; operator can hold manually
    else:
        status = "ok"
    return {"status": status, "flags": flags}


def assert_confirmable(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Lines that will post to PIMAS. Held lines are skipped; blocking mismatches raise."""
    ready: list[dict[str, Any]] = []
    for line in receipt.get("lines") or []:
        status = str(line.get("status") or "ok").lower()
        qty = float(line.get("qty") or 0)
        if qty <= 0:
            continue
        if status == "hold":
            continue
        if status == "mismatch" and not bool(line.get("force_ok")):
            raise HqReceiveError(
                "line_mismatch",
                f"รายการ {line.get('bcode')} ยังไม่ตรง — พักรายการหรือแก้ก่อนยืนยัน",
            )
        if not str(line.get("bcode") or "").strip():
            raise HqReceiveError("missing_bcode", "มีรายการที่ไม่มีรหัสสินค้า")
        ready.append(line)
    if not ready:
        raise HqReceiveError("empty_lines", "ไม่มีรายการที่จะรับเข้า (หรือพักทั้งหมด)")
    return ready


RULES_SUMMARY = """
HQ-only vendor receive rules
- Operator confirmation is required before PARTS9 writes.
- Partial receive is allowed; remaining qty stays on ICLOW until a later receive.
- Lines marked hold are not written to PIMAS in that confirm.
- Cost mismatch over tolerance (default 2%) and qty over open ICLOW are flagged.
- Over-PO qty blocks confirm unless the line is held or force_ok is set by a future privilege path.
- HQ_RECEIVE_PIMAS_WRITE_ENABLED=false → dry-run only (default).
- Stickers print only from confirmed (or dry-run preview) receipt lines with qty > 0.
- AI extract/match is assistive; unmatched or low-confidence lines stay editable.
""".strip()
