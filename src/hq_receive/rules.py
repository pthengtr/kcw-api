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

VARIANCE_CREDIT_NOTE = "credit_note"
VARIANCE_WAIT_REST = "wait_rest"
VARIANCE_CHANGE_PRODUCT = "change_product"
VARIANCE_ACTIONS = {
    VARIANCE_CREDIT_NOTE,
    VARIANCE_WAIT_REST,
    VARIANCE_CHANGE_PRODUCT,
}


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


def line_bill_qty(line: dict[str, Any]) -> float:
    if line.get("bill_qty") is not None:
        return float(line.get("bill_qty") or 0)
    return float(line.get("qty") or 0)


def line_received_qty(line: dict[str, Any]) -> float:
    if line.get("received_qty") is not None:
        return float(line.get("received_qty") or 0)
    return line_bill_qty(line)


def line_has_qty_variance(line: dict[str, Any]) -> bool:
    return qty_mismatch(line_bill_qty(line), line_received_qty(line))


def line_pi_qty(line: dict[str, Any]) -> float:
    """Qty written to the purchase invoice (PIMAS BILLTYPE=1)."""
    action = str(line.get("variance_action") or "").strip().lower()
    bill = line_bill_qty(line)
    received = line_received_qty(line)
    if line_has_qty_variance(line) and action == VARIANCE_CREDIT_NOTE:
        return bill
    if line_has_qty_variance(line) and action == VARIANCE_WAIT_REST:
        return received
    # No variance (or change_product held elsewhere): prefer bill qty for money,
    # falling back to received when bill is blank.
    return bill if bill > 0 else received


def line_cn_qty(line: dict[str, Any]) -> float:
    """Positive shortfall qty to credit-note (written as negative on PIDET)."""
    action = str(line.get("variance_action") or "").strip().lower()
    if action != VARIANCE_CREDIT_NOTE:
        return 0.0
    bill = line_bill_qty(line)
    received = line_received_qty(line)
    diff = bill - received
    if diff <= qty_tolerance():
        return 0.0
    return round(diff, 4)


def line_sticker_qty(line: dict[str, Any]) -> float:
    """Physical stickers follow goods actually received."""
    received = line_received_qty(line)
    if received > 0:
        return received
    return line_pi_qty(line)


def assert_variance_resolved(receipt: dict[str, Any]) -> None:
    """Every bill-vs-received mismatch must pick credit_note / wait_rest / change_product."""
    for line in receipt.get("lines") or []:
        status = str(line.get("status") or "ok").lower()
        if status == "hold":
            continue
        if not line_has_qty_variance(line):
            continue
        action = str(line.get("variance_action") or "").strip().lower()
        bill = line_bill_qty(line)
        received = line_received_qty(line)
        if received > bill + qty_tolerance():
            raise HqReceiveError(
                "qty_over_bill",
                f"รายการ {line.get('bcode')} รับจริงมากกว่าบิล — แก้จำนวนหรือพักรายการ",
            )
        if action not in VARIANCE_ACTIONS:
            raise HqReceiveError(
                "variance_unresolved",
                f"รายการ {line.get('bcode')} จำนวนบิล≠รับจริง — เลือกทำใบลดหนี้ / รอของตามมา / เปลี่ยนสินค้า",
            )
        if action == VARIANCE_CREDIT_NOTE and line_cn_qty(line) <= 0:
            raise HqReceiveError(
                "credit_note_empty",
                f"รายการ {line.get('bcode')} ไม่มีส่วนต่างสำหรับใบลดหนี้",
            )
        if action == VARIANCE_CHANGE_PRODUCT:
            raise HqReceiveError(
                "change_product_hold",
                f"รายการ {line.get('bcode')} เลือกเปลี่ยนสินค้า — พักรายการก่อนยืนยัน",
            )


def assert_confirmable(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Lines that will post to PIMAS. Held lines are skipped; blocking mismatches raise."""
    assert_variance_resolved(receipt)
    ready: list[dict[str, Any]] = []
    for line in receipt.get("lines") or []:
        status = str(line.get("status") or "ok").lower()
        pi_qty = line_pi_qty(line)
        if pi_qty <= 0:
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
        out = dict(line)
        out["qty"] = pi_qty
        out["bill_qty"] = line_bill_qty(line)
        out["received_qty"] = line_received_qty(line)
        ready.append(out)
    if not ready:
        raise HqReceiveError("empty_lines", "ไม่มีรายการที่จะรับเข้า (หรือพักทั้งหมด)")
    return ready


def credit_note_lines(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Lines (positive shortfall qty) that become a purchase credit note."""
    out: list[dict[str, Any]] = []
    for line in receipt.get("lines") or []:
        status = str(line.get("status") or "ok").lower()
        if status == "hold":
            continue
        cn_qty = line_cn_qty(line)
        if cn_qty <= 0:
            continue
        cost = float(line.get("cost") or 0)
        # Allocate line discount proportionally to CN qty vs bill qty when present.
        bill = line_bill_qty(line)
        disc = float(line.get("discount") or 0)
        cn_disc = round(disc * (cn_qty / bill), 2) if bill > 0 and disc else 0.0
        amount = round(max(0.0, cn_qty * cost - cn_disc), 2)
        out.append(
            {
                **dict(line),
                "qty": cn_qty,
                "discount": cn_disc,
                "amount": amount,
                "bill_qty": bill,
                "received_qty": line_received_qty(line),
            }
        )
    return out


RULES_SUMMARY = """
HQ-only vendor receive rules
- Operator confirmation is required before PARTS9 writes.
- Primary flow: choose vendor → select one or more open POs (with product preview) → review ค้างรับ lines.
- Partial receive is allowed; wait_rest reduces ICLOW.QTY and leaves the remainder as ค้างรับ.
- Full receive / credit-note path stamps ICLOW RECEIVED='Y'.
- Lines marked hold are not written to PIMAS in that confirm.
- When bill qty ≠ received qty, operator must choose: credit note / wait for rest / change product.
- Credit-note path: PI posts bill qty, CN posts the shortfall (negative), stock nets to received qty.
- Wait-rest path: PI posts received qty only.
- Change-product path: hold the line before confirm.
- Non-VAT CN billno KCCN…; VAT temp CN billno 7KCCN… (fill vendor CN no/date later).
- Draft cost defaults to ICMAS COSTLAST (else COSTNET); operator may type over it.
- New products can be created inline into HQ ICMAS from the receive page (manual BCODE; LOCATION1 / CODE1 / PRICE1 / cost).
- Draft lines can edit ICMAS identity fields via PUT /api/products/{bcode}.
- Cost mismatch over tolerance (default 2%) and qty over open ICLOW are flagged.
- Over-PO qty blocks confirm unless the line is held or force_ok is set by a future privilege path.
- HQ_RECEIVE_PIMAS_WRITE_ENABLED=false → dry-run only (default); product create / update also gated.
- Stickers print only from confirmed (or dry-run preview) receipt lines with received qty > 0.
- AI bill OCR may prefill header fields only; product lines come from selected POs.
""".strip()
