"""Confirm and cancel. Supabase holds the PO. ICLOW holds the ordered line."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.hq_po.config import get_hq_po_settings
from src.hq_po.db import (
    get_hq_po_supabase_client,
    get_order,
    insert_order,
    list_orders,
    mark_line_canceled,
    mark_order_canceled,
)
from src.hq_po.docno import make_docno, make_short_id
from src.hq_po.guards import (
    HqPoError,
    chosen_pack,
    plan_cancel,
    plan_confirm,
    plan_created,
    receive_view,
)
from src.hq_po.iclow_read import (
    fetch_bcode_suppliers,
    fetch_iclow_by_ids,
    fetch_incoming_qty,
    fetch_sheet_products,
    fetch_unordered_bcodes,
    fetch_vendor_names,
    supplier_choices,
)
from src.hq_po.insight import (
    ai_recommendation,
    build_insight_only_item,
    clean_propose_meta,
    load_insight_policies,
)
from src.hq_po.stamp import cancel_created, insert_ordered_lines, revert_ordered, stamp_ordered
from src.hq_po.suggest import attach_catalog, build_insight_only, build_suggest, suppliers_for_bcode


def suggest_payload() -> dict[str, Any]:
    settings = get_hq_po_settings()
    payload = build_suggest()
    payload["stamp_enabled"] = settings.stamp_enabled
    return payload


def insight_only_payload() -> dict[str, Any]:
    return build_insight_only()


def suppliers_payload(bcode: str, *, current: str = "", current_name: str = "") -> dict[str, Any]:
    code = str(bcode or "").strip()
    if not code:
        raise HqPoError("missing", "ไม่มีรหัสสินค้า")
    try:
        rows = suppliers_for_bcode(code, current=current, current_name=current_name)
    except Exception as exc:
        raise HqPoError("vendor_mismatch", "ตรวจเจ้าหนี้ทางเลือกไม่ได้") from exc
    return {"suppliers": rows}


def peers_payload(bcode: str) -> dict[str, Any]:
    from src.hq_po.peers import load_peers

    return load_peers(bcode)


def _vendor_name(acctno: str, hinted: str | None) -> str | None:
    name = (hinted or "").strip()
    if name:
        return name
    if not acctno:
        return None
    return fetch_vendor_names([acctno]).get(acctno)


def _split_lines(lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    for line in lines:
        try:
            iclow_id = int(line.get("iclow_id"))
        except (TypeError, ValueError):
            iclow_id = 0
        if iclow_id > 0:
            existing.append(line)
        else:
            created.append(line)
    return existing, created


def _resolve_created(bcodes: list[str]) -> dict[str, dict[str, Any]]:
    """Fresh AI qty for products that are not already waiting on ICLOW."""
    from src.hq_po.stock import fetch_dual_stock, fetch_parts9_qty, refresh_qtyoh2

    codes = []
    seen: set[str] = set()
    for raw in bcodes:
        bcode = str(raw or "").strip()
        if bcode and bcode not in seen:
            seen.add(bcode)
            codes.append(bcode)
    if not codes:
        return {}
    refresh_qtyoh2(codes)
    unordered = fetch_unordered_bcodes(codes)
    incoming = fetch_incoming_qty()
    try:
        parts9 = fetch_parts9_qty(codes)
    except Exception:
        parts9 = {}
    policies = load_insight_policies()
    hq, syp, ok = fetch_dual_stock(codes)
    if not ok:
        raise HqPoError("stock_unavailable", "อ่านสต็อกเพื่อสั่ง AI ไม่สำเร็จ")
    out: dict[str, dict[str, Any]] = {}
    for bcode in codes:
        if bcode in unordered:
            raise HqPoError("already_on_iclow", f"{bcode} มีในรายการรอสั่งแล้ว ให้สั่งจากแถว ICLOW")
        policy = policies.get(bcode)
        if not policy:
            raise HqPoError("not_confirmable", f"{bcode} ไม่มีคำแนะนำ AI")
        hq_meta = hq.get(bcode) or {"qtyoh2": 0, "blocked": False, "mtp2": 1}
        syp_meta = syp.get(bcode) or {"qtyoh2": 0, "blocked": False, "mtp2": 1}
        if bcode not in hq and bcode not in syp:
            raise HqPoError("missing", f"ไม่พบสินค้า {bcode}")
        if hq_meta.get("blocked"):
            raise HqPoError("not_confirmable", f"{bcode} ไม่สั่งเพิ่ม")
        hq_qty = float(hq_meta.get("qtyoh2") or 0)
        syp_qty = float(syp_meta.get("qtyoh2") or 0)
        mtp = hq_meta.get("mtp2") or syp_meta.get("mtp2")
        advice = None
        if policy:
            advice = ai_recommendation(
                policy,
                live_company=hq_qty + syp_qty,
                mtp2=float(mtp) if mtp not in (None, "") else None,
                incoming=float(incoming.get(bcode) or 0),
            )
        if advice and policy:
            item = build_insight_only_item(policy, advice, hq_meta=hq_meta, syp_meta=syp_meta)
        else:
            vendor = str((policy or {}).get("last_supplier") or "").strip()
            item = {
                "iclow_id": None,
                "vendor": vendor,
                "bcode": bcode,
                "descr": (hq_meta.get("descr") or syp_meta.get("descr") or "").strip(),
                "mcode": (hq_meta.get("mcode") or syp_meta.get("mcode") or "").strip(),
                "qty": 0,
                "ui": (hq_meta.get("ui1") or syp_meta.get("ui1") or "").strip(),
                "source": "insight",
                "propose_meta": {"source": "insight"},
            }
        if not str(item.get("vendor") or "").strip():
            raise HqPoError("vendor_mismatch", f"{bcode} ไม่มีเจ้าหนี้")
        meta = dict(item.get("propose_meta") or {})
        meta["iclow_origin"] = "created"
        if parts9.get(bcode):
            meta["parts9_qty"] = parts9[bcode]
        item["propose_meta"] = meta
        out[bcode] = item
    return out


def _created_flag(line: dict[str, Any]) -> bool:
    meta = line.get("propose_meta")
    return isinstance(meta, dict) and meta.get("iclow_origin") == "created"


def _peer_flag(line: dict[str, Any]) -> bool:
    meta = line.get("propose_meta")
    return isinstance(meta, dict) and meta.get("iclow_origin") == "peer"


def _line_bcode(raw: dict[str, Any], live_by_id: dict[int, dict[str, Any]]) -> str:
    try:
        iclow_id = int(raw.get("iclow_id"))
    except (TypeError, ValueError):
        iclow_id = 0
    if iclow_id > 0:
        return str((live_by_id.get(iclow_id) or {}).get("bcode") or "").strip()
    return str(raw.get("bcode") or "").strip()


def _apply_units(
    lines: list[dict[str, Any]],
    *,
    products: dict[str, dict[str, Any]],
    live_by_id: dict[int, dict[str, Any]] | None = None,
) -> None:
    """Keep a chosen UI1/UI2. Drop a unit that is not a pack on that product."""
    live_by_id = live_by_id or {}
    for raw in lines:
        product = products.get(_line_bcode(raw, live_by_id)) or {}
        pack = chosen_pack(raw.get("ui"), product)
        if pack is None:
            raw.pop("ui", None)
            raw.pop("mtp", None)
            continue
        raw["ui"], raw["mtp"] = pack


def _assert_supplier_choices(
    lines: list[dict[str, Any]],
    *,
    live_by_id: dict[int, dict[str, Any]],
    resolved: dict[str, dict[str, Any]],
) -> None:
    """A switched vendor must be a real purchase account or the catalog vendor."""
    changed: list[tuple[str, str]] = []
    for raw in lines:
        asked = str(raw.get("vendor") or "").strip()
        if not asked:
            continue
        try:
            iclow_id = int(raw.get("iclow_id"))
        except (TypeError, ValueError):
            iclow_id = 0
        if iclow_id > 0:
            live = live_by_id.get(iclow_id) or {}
            current = str(live.get("vendor") or "").strip()
            bcode = str(live.get("bcode") or "").strip()
        else:
            bcode = str(raw.get("bcode") or "").strip()
            current = str((resolved.get(bcode) or {}).get("vendor") or "").strip()
        if bcode and asked != current:
            changed.append((bcode, asked))
    if not changed:
        return
    try:
        history, catalog = fetch_bcode_suppliers([bcode for bcode, _ in changed])
    except Exception as exc:
        raise HqPoError("vendor_mismatch", "ตรวจเจ้าหนี้ทางเลือกไม่ได้") from exc
    for bcode, asked in changed:
        known = {str(row.get("acctno") or "").strip() for row in history.get(bcode) or []}
        cat = str((catalog.get(bcode) or {}).get("acctno") or "").strip()
        if cat:
            known.add(cat)
        if asked not in known:
            raise HqPoError("vendor_mismatch", f"{bcode} ไม่เคยรับจาก {asked}")


def _resolve_peer(lines: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """A replacement code ordered as its own line. It does not need an AI policy."""
    codes = []
    seen: set[str] = set()
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        if bcode and bcode not in seen:
            seen.add(bcode)
            codes.append(bcode)
    if not codes:
        return {}
    unordered = fetch_unordered_bcodes(codes)
    try:
        products = fetch_sheet_products(codes)
    except Exception as exc:
        raise HqPoError("missing", "อ่านสินค้าแทนไม่สำเร็จ") from exc
    try:
        history, catalog = fetch_bcode_suppliers(codes)
    except Exception as exc:
        raise HqPoError("vendor_mismatch", "ตรวจเจ้าหนี้ของสินค้าแทนไม่ได้") from exc
    out: dict[str, dict[str, Any]] = {}
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        if not bcode or bcode in out:
            continue
        if bcode in unordered:
            raise HqPoError("already_on_iclow", f"{bcode} มีในรายการรอสั่งแล้ว ให้สั่งจากแถวนั้น")
        product = products.get(bcode) or {}
        if not product:
            raise HqPoError("missing", f"ไม่พบสินค้า {bcode}")
        asked = str(raw.get("vendor") or "").strip()
        card = catalog.get(bcode) or {}
        choices = supplier_choices(
            history.get(bcode) or [],
            catalog=str(card.get("acctno") or ""),
            catalog_name=str(card.get("name") or ""),
        )
        known = {str(row.get("acctno") or "").strip() for row in choices}
        if not asked or asked not in known:
            raise HqPoError("vendor_mismatch", f"{bcode} ไม่มีเจ้าหนี้ที่สั่งได้")
        pack = chosen_pack(raw.get("ui"), product)
        ui = pack[0] if pack else str(product.get("ui") or "").strip()
        out[bcode] = {
            "iclow_id": None,
            "vendor": asked,
            "bcode": bcode,
            "descr": str(product.get("descr") or "").strip(),
            "mcode": str(product.get("mcode") or "").strip(),
            "qty": 0,
            "ui": ui or None,
            "source": "peer",
            "propose_meta": {"iclow_origin": "created", "peer": True},
        }
    return out


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
    existing, created = _split_lines(lines)
    peers = [line for line in created if _peer_flag(line)]
    ai_lines = [line for line in created if not _peer_flag(line)]
    planned: list[dict[str, Any]] = []
    if existing:
        ids = [int(line["iclow_id"]) for line in existing]
        live = fetch_iclow_by_ids(ids)
        try:
            products = fetch_sheet_products(
                [str((live.get(iclow_id) or {}).get("bcode") or "") for iclow_id in ids]
            )
        except Exception:
            products = {}
        _apply_units(existing, products=products, live_by_id=live)
        _assert_supplier_choices(existing, live_by_id=live, resolved={})
        planned.extend(plan_confirm(existing, live, vendor=vendor))
    if ai_lines:
        resolved = _resolve_created([str(line.get("bcode") or "") for line in ai_lines])
        _assert_supplier_choices(ai_lines, live_by_id={}, resolved=resolved)
        planned.extend(plan_created(ai_lines, resolved, vendor=vendor))
    if peers:
        resolved_peers = _resolve_peer(peers)
        _assert_supplier_choices(peers, live_by_id={}, resolved=resolved_peers)
        planned.extend(plan_created(peers, resolved_peers, vendor=vendor))
    if not planned:
        raise HqPoError("empty", "ยังไม่ได้เลือกรายการ")
    to_stamp = [line for line in planned if not _created_flag(line)]
    to_insert = [line for line in planned if _created_flag(line)]
    if to_insert:
        from src.hq_po.stock import refresh_qtyoh2

        refresh_qtyoh2([str(line.get("bcode") or "") for line in to_insert])
    for line in to_stamp:
        line["propose_meta"] = clean_propose_meta(line.get("propose_meta"))
    acct = (vendor or "").strip()
    name = _vendor_name(acct, vendor_name)
    client = get_hq_po_supabase_client()
    last_error: Exception | None = None
    for _ in range(3):
        short_id = make_short_id()
        docno = make_docno(short_id, date.today())
        inserted = insert_ordered_lines(to_insert, docno=docno) if to_insert else []
        stored_lines = to_stamp + inserted
        try:
            order = insert_order(
                client,
                short_id=short_id,
                docno=docno,
                vendor_acctno=acct,
                vendor_name=name,
                ordered_by=ordered_by,
                lines=stored_lines,
            )
        except Exception as exc:
            if inserted:
                cancel_created(inserted, docno=docno)
            message = str(exc).lower()
            if "hq_po_lines_open_iclow" in message:
                raise HqPoError("already_ordered", "มีรายการที่อยู่ในใบสั่งซื้อแล้ว") from exc
            if "duplicate" in message or "unique" in message or "23505" in message:
                last_error = exc
                continue
            raise HqPoError("supabase_write", str(exc)) from exc
        try:
            if to_stamp:
                stamp_ordered(to_stamp, docno=docno)
        except Exception:
            mark_order_canceled(client, order["order_id"], reason="stamp_failed")
            if inserted:
                cancel_created(inserted, docno=docno)
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
    lines = [line for order in orders for line in (order.get("lines") or [])]
    attach_catalog(lines)
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
    created = [line for line in pending if _created_flag(line)]
    stamped = [line for line in pending if not _created_flag(line)]
    if stamped:
        revert_ordered(stamped, docno=docno)
    if created:
        cancel_created(created, docno=docno)
    mark_order_canceled(client, order_id, reason=reason or "canceled")
    return get_order(client, order_id) or {"order_id": order_id, "status": "canceled"}


def cancel_order_line(order_id: str, line_id: str, *, reason: str | None = None) -> dict[str, Any]:
    """Drop one line the vendor cannot supply and return that ICLOW row to รอสั่ง."""
    settings = get_hq_po_settings()
    if not settings.stamp_enabled:
        raise HqPoError(
            "stamp_disabled",
            "ยังไม่เปิด HQ_PO_ICLOW_STAMP_ENABLED จึงยังไม่ยกเลิกบน ICLOW",
        )
    wanted = str(line_id or "").strip()
    if not wanted:
        raise HqPoError("missing", "ไม่มีรายการให้ยกเลิก")
    client = get_hq_po_supabase_client()
    order = get_order(client, order_id)
    if not order or order.get("status") != "ordered":
        raise HqPoError("missing", "ไม่พบใบสั่งซื้อที่ยังเปิดอยู่")
    line = next(
        (
            row
            for row in (order.get("lines") or [])
            if str(row.get("line_id") or "") == wanted and not row.get("canceled_at")
        ),
        None,
    )
    if not line:
        raise HqPoError("missing", "ไม่พบรายการนี้ในใบสั่งซื้อ")
    try:
        iclow_id = int(line["iclow_id"])
    except (TypeError, ValueError):
        raise HqPoError("missing", "รายการนี้ไม่มีแถว ICLOW") from None
    live = fetch_iclow_by_ids([iclow_id])
    row = live.get(iclow_id)
    if not row:
        raise HqPoError("missing", f"ไม่พบ ICLOW {iclow_id}")
    docno = str(order.get("docno") or "")
    plan_cancel([row], docno)
    # A line the vendor cannot fill goes back to the waiting list, including a
    # row this app inserted. Whole-order cancel still retires those inserted rows.
    revert_ordered([line], docno=docno)
    mark_line_canceled(client, order_id, wanted, reason=reason or "vendor_unavailable")
    return get_order(client, order_id) or {"order_id": order_id, "status": "ordered"}
