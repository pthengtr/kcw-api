from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def qty_open_prepare(qty_requested: float, qty_prepared: float) -> float:
    return max(float(qty_requested or 0) - float(qty_prepared or 0), 0.0)


def qty_open_receive(qty_prepared: float, qty_received: float) -> float:
    return max(float(qty_prepared or 0) - float(qty_received or 0), 0.0)


def qty_short_vs_order(qty_requested: float, qty_actual: float) -> float:
    return max(float(qty_requested or 0) - float(qty_actual or 0), 0.0)


def _line_cancelled_unprepared(line: dict[str, Any]) -> bool:
    """True when the line was closed before anything was prepared."""
    if float(line.get("qty_prepared") or 0) > 0:
        return False
    if line.get("cancelled_at"):
        return True
    return (line.get("line_status") or "") == "cancelled"


def shipment_lines_fully_received(shipment_lines: list[dict[str, Any]]) -> bool:
    if not shipment_lines:
        return False
    for sl in shipment_lines:
        shipped = float(sl.get("qty_shipped") or 0)
        received = float(sl.get("qty_received") or 0)
        if shipped > 0 and received < shipped:
            return False
    return True


def request_has_open_prepare(lines: list[dict[str, Any]]) -> bool:
    """True when at least one active line still needs prepare qty."""
    active = [ln for ln in lines if not ln.get("cancelled_at")]
    return any(
        qty_open_prepare(ln.get("qty_requested", 0), ln.get("qty_prepared", 0)) > 0 for ln in active
    )


def derive_line_status(
    *,
    qty_requested: float,
    qty_prepared: float,
    qty_received: float,
    cancelled: bool = False,
) -> str:
    """open → prepared → received. Cancelled only when nothing was prepared.

    qty_requested is not a status input: a short ship is received once the
    prepared qty has been received.
    """
    del qty_requested  # kept for callers; status follows prepared vs received
    prep = float(qty_prepared or 0)
    recv = float(qty_received or 0)
    if cancelled and prep <= 0:
        return "cancelled"
    if prep > 0 and recv >= prep:
        return "received"
    if prep > 0:
        return "prepared"
    return "open"


def last_received_at(
    ships: list[dict[str, Any]],
    receipts_by_shipment: dict[str, list[dict[str, Any]]],
) -> str | None:
    """Latest receipt created_at across shipments (ISO timestamp), or None."""
    latest: str | None = None
    for ship in ships:
        sid = ship.get("shipment_id")
        if not sid:
            continue
        for rc in receipts_by_shipment.get(sid) or []:
            ts = rc.get("created_at")
            if not ts:
                continue
            ts_s = str(ts)
            if latest is None or ts_s > latest:
                latest = ts_s
    return latest


def summarize_request_progress(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Receive totals for lists (barcode button). Status is separate."""
    active = [ln for ln in lines if not _line_cancelled_unprepared(ln)]
    qty_received_total = 0.0
    received_line_count = 0
    for ln in active:
        recv = float(ln.get("qty_received") or 0)
        qty_received_total += max(recv, 0.0)
        if recv > 0:
            received_line_count += 1
    return {
        "qty_received_total": qty_received_total,
        "received_line_count": received_line_count,
        "has_received": received_line_count > 0,
    }


def derive_request_status(
    *,
    header_status: str,
    lines: list[dict[str, Any]],
    has_shipments: bool,
) -> str:
    """requested → prepared → received.

    received means every prepared qty is in. Shortfall versus qty_requested
    does not keep the request open — a new ICLOW covers stock still at the low.
    """
    if header_status == "draft":
        return "draft"
    if header_status == "cancelled":
        return "cancelled"

    considered = [ln for ln in lines if not _line_cancelled_unprepared(ln)]
    if lines and not considered:
        return "cancelled"

    any_prepared = any(float(ln.get("qty_prepared") or 0) > 0 for ln in considered)
    any_open_recv = any(
        qty_open_receive(ln.get("qty_prepared", 0), ln.get("qty_received", 0)) > 0
        for ln in considered
    )
    if any_open_recv or (has_shipments and not any_prepared):
        return "prepared"
    if any_prepared:
        return "received"
    if has_shipments:
        return "prepared"
    return "requested"


@dataclass
class ActionResult:
    allowed: bool
    reason: str = ""


def _line_qty_requested(line: dict[str, Any]) -> float:
    return float(line.get("qty_requested") or line.get("qty") or 0)


def can_action(action: str, ctx: dict[str, Any]) -> ActionResult:
    """Return whether an action is allowed. ctx keys vary by action."""
    if action == "submit_transfer":
        lines = ctx.get("lines") or []
        if not lines:
            return ActionResult(False, "ต้องมีอย่างน้อย 1 รายการ")
        if any(_line_qty_requested(ln) <= 0 for ln in lines):
            return ActionResult(False, "จำนวนต้องมากกว่า 0")
        bcodes = [str(ln.get("bcode") or "").strip() for ln in lines]
        if len(bcodes) != len(set(bcodes)):
            return ActionResult(False, "รหัสสินค้าซ้ำในคำขอเดียวกัน")
        return ActionResult(True)

    if action == "cancel_request":
        if ctx.get("has_shipments"):
            return ActionResult(False, "ยกเลิกไม่ได้หลังมีใบ TF แล้ว")
        status = ctx.get("status") or ""
        if status == "requested":
            return ActionResult(True)
        if status in ("draft", "received", "complete", "cancelled"):
            return ActionResult(False, "สถานะนี้ยกเลิกไม่ได้")
        # No shipments yet — allow cancel even if status drifted.
        return ActionResult(True)

    if action == "delete_draft":
        if (ctx.get("status") or "draft") != "draft":
            return ActionResult(False, "ลบได้เฉพาะร่างที่ยังไม่ส่ง")
        return ActionResult(True)

    if action == "edit_draft":
        if (ctx.get("status") or "draft") != "draft":
            return ActionResult(False, "แก้ไขได้เฉพาะร่างที่ยังไม่ส่ง")
        return ActionResult(True)

    if action in ("hq_prepare", "prepare_ship"):
        if ctx.get("cancelled_at"):
            return ActionResult(False, "รายการนี้ปิดแล้ว")
        header_status = ctx.get("status") or "requested"
        if ctx.get("has_shipments") or float(ctx.get("qty_prepared") or 0) > 0:
            return ActionResult(False, "จัดได้ครั้งเดียวต่อคำขอ")
        if header_status != "requested":
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
