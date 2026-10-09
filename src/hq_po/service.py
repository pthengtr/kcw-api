"""Confirm and cancel. Supabase holds the PO. ICLOW gets the ordered stamp only."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.hq_po.config import get_hq_po_settings
from src.hq_po.db import (
    get_hq_po_supabase_client,
    get_order,
    insert_order,
    list_orders,
    mark_order_canceled,
)
from src.hq_po.docno import make_docno, make_short_id
from src.hq_po.guards import HqPoError, plan_cancel, plan_confirm, receive_view
from src.hq_po.iclow_read import fetch_iclow_by_ids, fetch_vendor_names
from src.hq_po.insight import clean_propose_meta
from src.hq_po.stamp import revert_ordered, stamp_ordered
from src.hq_po.suggest import build_suggest


def suggest_payload() -> dict[str, Any]:
    settings = get_hq_po_settings()
    payload = build_suggest()
    payload["stamp_enabled"] = settings.stamp_enabled
    return payload


def _vendor_name(acctno: str, hinted: str | None) -> str | None:
    name = (hinted or "").strip()
    if name:
        return name
    if not acctno:
        return None
    return fetch_vendor_names([acctno]).get(acctno)


def confirm_order(
    *,
    vendor: str,
    vendor_name: str | None,
    lines: list[dict[str, Any]],
    ordered_by: str | None,
) -> dict[str, Any]:
    settings = get_hq_po_settings()
    if not settings.stamp_enabled:
        raise HqPoError(
            "stamp_disabled",
            "ยังไม่เปิด HQ_PO_ICLOW_STAMP_ENABLED จึงยังไม่บันทึกใบสั่งซื้อ",
        )
    ids: list[int] = []
    for line in lines:
        try:
            ids.append(int(line.get("iclow_id")))
        except (TypeError, ValueError):
            ids.append(0)
    live = fetch_iclow_by_ids(ids)
    planned = plan_confirm(lines, live, vendor=vendor)
    for line in planned:
        line["propose_meta"] = clean_propose_meta(line.get("propose_meta"))
    acct = (vendor or "").strip()
    name = _vendor_name(acct, vendor_name)
    client = get_hq_po_supabase_client()
    last_error: Exception | None = None
    for _ in range(3):
        short_id = make_short_id()
        docno = make_docno(short_id, date.today())
        try:
            order = insert_order(
                client,
                short_id=short_id,
                docno=docno,
                vendor_acctno=acct,
                vendor_name=name,
                ordered_by=ordered_by,
                lines=planned,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "hq_po_lines_open_iclow" in message:
                raise HqPoError("already_ordered", "มีรายการที่อยู่ในใบสั่งซื้อแล้ว") from exc
            if "duplicate" in message or "unique" in message or "23505" in message:
                last_error = exc
                continue
            raise HqPoError("supabase_write", str(exc)) from exc
        try:
            stamp_ordered(planned, docno=docno)
        except Exception:
            mark_order_canceled(client, order["order_id"], reason="stamp_failed")
            raise
        order["vendor_name"] = name
        return order
    raise HqPoError("docno_collision", f"ออกเลขที่ใบซ้ำ: {last_error}")


def _attach_receive(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids: list[int] = []
    for order in orders:
        for line in order.get("lines") or []:
            try:
                ids.append(int(line.get("iclow_id")))
            except (TypeError, ValueError):
                continue
    try:
        live = fetch_iclow_by_ids(ids)
    except Exception:
        live = {}
    rcvdnos = [
        str(row.get("rcvdno") or "").strip()
        for row in live.values()
        if str(row.get("received") or "").upper() == "Y" and str(row.get("rcvdno") or "").strip()
    ]
    pimas: dict[str, dict[str, Any]] = {}
    if rcvdnos:
        try:
            from src.ops.pi import resolve_pimas_batch

            pimas = resolve_pimas_batch(rcvdnos)
        except Exception:
            pimas = {}
    for order in orders:
        received_n = 0
        open_n = 0
        for line in order.get("lines") or []:
            try:
                iclow_id = int(line.get("iclow_id"))
            except (TypeError, ValueError):
                iclow_id = 0
            row = live.get(iclow_id)
            rcvdno = str((row or {}).get("rcvdno") or "").strip()
            view = receive_view(row, pimas.get(rcvdno))
            line["receive"] = view
            if view.get("received"):
                received_n += 1
            elif not view.get("unknown"):
                open_n += 1
        order["received_count"] = received_n
        order["open_count"] = open_n
        if received_n and not open_n:
            order["receive_label"] = "รับแล้ว"
        elif received_n:
            order["receive_label"] = "รับบางส่วน"
        else:
            order["receive_label"] = "ค้างรับ"
    return orders


def list_open_orders() -> list[dict[str, Any]]:
    client = get_hq_po_supabase_client()
    return _attach_receive(list_orders(client))


def cancel_order(order_id: str, *, reason: str | None = None) -> dict[str, Any]:
    settings = get_hq_po_settings()
    if not settings.stamp_enabled:
        raise HqPoError(
            "stamp_disabled",
            "ยังไม่เปิด HQ_PO_ICLOW_STAMP_ENABLED จึงยังไม่ยกเลิกบน ICLOW",
        )
    client = get_hq_po_supabase_client()
    order = get_order(client, order_id)
    if not order or order.get("status") != "ordered":
        raise HqPoError("missing", "ไม่พบใบสั่งซื้อที่ยังเปิดอยู่")
    lines = [line for line in (order.get("lines") or []) if not line.get("canceled_at")]
    if not lines:
        raise HqPoError("empty", "ใบนี้ไม่มีรายการ")
    live = fetch_iclow_by_ids([int(line["iclow_id"]) for line in lines])
    live_rows = []
    for line in lines:
        row = live.get(int(line["iclow_id"]))
        if not row:
            raise HqPoError("missing", f"ไม่พบ ICLOW {line['iclow_id']}")
        live_rows.append(row)
    docno = str(order.get("docno") or "")
    plan_cancel(live_rows, docno)
    pending = [
        line
        for line in lines
        if str(live.get(int(line["iclow_id"]), {}).get("docno") or "").strip() == docno
    ]
    if pending:
        revert_ordered(pending, docno=docno)
    mark_order_canceled(client, order_id, reason=reason or "canceled")
    return get_order(client, order_id) or {"order_id": order_id, "status": "canceled"}
