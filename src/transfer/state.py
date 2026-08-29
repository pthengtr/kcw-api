from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def qty_open_prepare(qty_requested: float, qty_prepared: float) -> float:
    return max(float(qty_requested or 0) - float(qty_prepared or 0), 0.0)


def qty_open_receive(qty_prepared: float, qty_received: float) -> float:
    return max(float(qty_prepared or 0) - float(qty_received or 0), 0.0)


def derive_line_status(
    *,
    qty_requested: float,
    qty_prepared: float,
    qty_received: float,
    cancelled: bool = False,
) -> str:
    if cancelled:
        return "cancelled"
    req = float(qty_requested or 0)
    prep = float(qty_prepared or 0)
    recv = float(qty_received or 0)
    if prep <= 0:
        return "open"
    if recv >= req:
        return "complete"
    if recv > 0:
        return "partial_received"
    if prep >= req:
        return "prepared"
    return "partial_prepared"


def derive_request_status(
    *,
    header_status: str,
    lines: list[dict[str, Any]],
    has_shipments: bool,
) -> str:
    if header_status == "draft":
        return "draft"
    if header_status == "cancelled":
        return "cancelled"

    active = [ln for ln in lines if not ln.get("cancelled_at")]
    if not active:
        return "cancelled"

    if all(ln.get("line_status") == "complete" for ln in active):
        return "complete"

    any_recv = any(float(ln.get("qty_received") or 0) > 0 for ln in active)
    any_prep = any(float(ln.get("qty_prepared") or 0) > 0 for ln in active)
    any_open_prep = any(
        qty_open_prepare(ln.get("qty_requested", 0), ln.get("qty_prepared", 0)) > 0 for ln in active
    )
    any_open_recv = any(
        qty_open_receive(ln.get("qty_prepared", 0), ln.get("qty_received", 0)) > 0 for ln in active
    )

    if any_recv and not all(ln.get("line_status") == "complete" for ln in active):
        return "partial_received"
    if has_shipments and any_open_recv:
        return "awaiting_receive"
    if any_prep and any_open_prep:
        return "partial_prepared"
    if any_prep:
        return "awaiting_receive"
    return "requested"


@dataclass
class ActionResult:
    allowed: bool
    reason: str = ""


def can_action(action: str, ctx: dict[str, Any]) -> ActionResult:
    """Return whether an action is allowed. ctx keys vary by action."""
    if action == "submit_transfer":
        lines = ctx.get("lines") or []
        if not lines:
            return ActionResult(False, "ต้องมีอย่างน้อย 1 รายการ")
        if any(float(ln.get("qty_requested") or 0) <= 0 for ln in lines):
            return ActionResult(False, "จำนวนต้องมากกว่า 0")
        bcodes = [str(ln.get("bcode") or "").strip() for ln in lines]
        if len(bcodes) != len(set(bcodes)):
            return ActionResult(False, "รหัสสินค้าซ้ำในคำขอเดียวกัน")
        return ActionResult(True)

    if action == "cancel_request":
        if ctx.get("has_shipments"):
            return ActionResult(False, "ยกเลิกไม่ได้หลังมีใบ TF แล้ว")
        if ctx.get("status") != "requested":
            return ActionResult(False, "ยกเลิกได้เฉพาะคำขอที่ส่งแล้วและยังไม่จัด")
        return ActionResult(True)

    if action == "cancel_line":
        if float(ctx.get("qty_prepared") or 0) > 0:
            return ActionResult(False, "ยกเลิกรายการไม่ได้หลังจัดแล้ว")
        return ActionResult(True)

    if action == "hq_prepare":
        if ctx.get("status") not in ("requested", "partial_prepared", "awaiting_receive"):
            return ActionResult(False, "สถานะคำขอไม่พร้อมจัด")
        qty_ship = float(ctx.get("qty_ship") or 0)
        if qty_ship <= 0:
            return ActionResult(False, "จำนวนจัดต้องมากกว่า 0")
        open_prep = qty_open_prepare(ctx.get("qty_requested", 0), ctx.get("qty_prepared", 0))
        if qty_ship > open_prep:
            return ActionResult(False, "จำนวนจัดเกินที่ขอค้างจัด")
        return ActionResult(True)

    if action == "syp_receive":
        if not ctx.get("tf_billno"):
            return ActionResult(False, "ยังไม่มีใบ TF")
        qty_recv = float(ctx.get("qty_receive") or 0)
        if qty_recv <= 0:
            return ActionResult(False, "จำนวนรับต้องมากกว่า 0")
        max_recv = float(ctx.get("qty_on_shipment") or 0)
        if qty_recv > max_recv:
            return ActionResult(False, "รับเกินจำนวนในใบ TF")
        total_recv = float(ctx.get("qty_received") or 0) + qty_recv
        if total_recv > float(ctx.get("qty_prepared") or 0):
            return ActionResult(False, "รับเกินจำนวนที่จัดแล้ว")
        return ActionResult(True)

    if action == "edit_qty_after_submit":
        return ActionResult(False, "แก้จำนวนหลังส่งคำขอไม่ได้")

    if action == "merge_requests":
        return ActionResult(False, "รวมคำขอบนใบ TF เดียวไม่ได้")

    return ActionResult(False, f"unknown action: {action}")


def make_short_id(transfer_id: str) -> str:
    clean = (transfer_id or "").replace("-", "")
    return f"TRF-{clean[:8].upper()}"
