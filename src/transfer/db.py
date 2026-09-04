from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from src.transfer.config import get_transfer_settings
from datetime import datetime, timezone

from src.transfer.state import derive_line_status, derive_request_status, make_short_id, prep_recv_mismatch, qty_open_prepare, qty_short_vs_order, request_has_open_prepare, summarize_request_progress
from src.transfer.parts9 import enrich_transfer_lines

TRANSFER_SCHEMA = "transfer"


class BumpError(RuntimeError):
    pass


@lru_cache
def get_transfer_supabase_client() -> Client:
    settings = get_transfer_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(TRANSFER_SCHEMA).from_(name)


def _first_row(resp) -> dict[str, Any]:
    data = resp.data
    if data is None:
        return {}
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data)


def _rows(resp) -> list[dict[str, Any]]:
    return [dict(r) for r in (resp.data or [])]


def list_need(client: Client) -> list[dict[str, Any]]:
    resp = _table(client, "need_list").select("*").order("created_at", desc=True).execute()
    return _rows(resp)


def upsert_need(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "need_list").upsert(row, on_conflict="bcode").select("*").execute()
    return _first_row(resp)


def delete_need(client: Client, need_id: str) -> None:
    _table(client, "need_list").delete().eq("need_id", need_id).execute()


def clear_need_list(client: Client) -> None:
    """Delete every need_list row (used when replacing the cart)."""
    _table(client, "need_list").delete().gte(
        "created_at", "1970-01-01T00:00:00+00:00"
    ).execute()


def replace_need_list(
    client: Client, rows: list[dict[str, Any]], *, actor: str
) -> list[dict[str, Any]]:
    """Clear the cart and upsert the provided rows in one server round."""
    clear_need_list(client)
    out: list[dict[str, Any]] = []
    for raw in rows:
        bcode = (raw.get("bcode") or "").strip()
        if not bcode:
            continue
        payload = {
            "bcode": bcode,
            "qty": raw.get("qty"),
            "descr": (raw.get("descr") or None),
            "suggest_qty": raw.get("suggest_qty") if raw.get("suggest_qty") is not None else raw.get("qty"),
            "hq_qtyoh2": raw.get("hq_qtyoh2"),
            "added_by": actor,
        }
        out.append(upsert_need(client, payload))
    return out


def list_lines_by_transfers(
    client: Client, transfer_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    ids = [t for t in transfer_ids if t]
    if not ids:
        return {}
    resp = (
        _table(client, "lines")
        .select("*")
        .in_("transfer_id", ids)
        .order("created_at")
        .execute()
    )
    by: dict[str, list[dict[str, Any]]] = {tid: [] for tid in ids}
    for row in _rows(resp):
        tid = row.get("transfer_id")
        if tid:
            by.setdefault(tid, []).append(row)
    return by


def list_shipments_by_transfers(
    client: Client, transfer_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    ids = [t for t in transfer_ids if t]
    if not ids:
        return {}
    resp = (
        _table(client, "shipments")
        .select("*")
        .in_("transfer_id", ids)
        .order("created_at")
        .execute()
    )
    by: dict[str, list[dict[str, Any]]] = {tid: [] for tid in ids}
    for row in _rows(resp):
        tid = row.get("transfer_id")
        if tid:
            by.setdefault(tid, []).append(row)
    return by


def list_shipment_lines_by_shipments(
    client: Client, shipment_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    ids = [s for s in shipment_ids if s]
    if not ids:
        return {}
    resp = (
        _table(client, "shipment_lines")
        .select("*")
        .in_("shipment_id", ids)
        .execute()
    )
    by: dict[str, list[dict[str, Any]]] = {sid: [] for sid in ids}
    for row in _rows(resp):
        sid = row.get("shipment_id")
        if sid:
            by.setdefault(sid, []).append(row)
    return by


def list_requests(
    client: Client,
    *,
    status: str | None = None,
    from_branch: str | None = None,
    to_branch: str | None = None,
    role: str | None = None,
    site: str | None = None,
) -> list[dict[str, Any]]:
    q = _table(client, "requests").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if from_branch:
        q = q.eq("from_branch", from_branch.upper())
    if to_branch:
        q = q.eq("to_branch", to_branch.upper())
    items = _rows(q.execute())
    if not role or not site:
        return items
    site_u = site.upper()
    role_l = role.lower()
    if role_l == "prepare":
        candidates = [
            r
            for r in items
            if (r.get("from_branch") or "HQ").upper() == site_u
            and (r.get("status") or "").lower() not in ("draft", "cancelled", "complete")
        ]
        lines_by = list_lines_by_transfers(
            client, [r["transfer_id"] for r in candidates]
        )
        out: list[dict[str, Any]] = []
        for r in candidates:
            lines = lines_by.get(r["transfer_id"]) or []
            if request_has_open_prepare(lines):
                out.append(r)
        return out
    if role_l == "receive":
        return [
            r
            for r in items
            if (r.get("to_branch") or "SYP").upper() == site_u
            and (r.get("status") or "") not in ("draft", "cancelled", "complete")
        ]
    if role_l == "mine":
        return [r for r in items if (r.get("to_branch") or "").upper() == site_u]
    return items


def get_request(client: Client, transfer_id: str) -> dict[str, Any]:
    resp = _table(client, "requests").select("*").eq("transfer_id", transfer_id).limit(1).execute()
    return _first_row(resp)


def list_lines(client: Client, transfer_id: str) -> list[dict[str, Any]]:
    resp = (
        _table(client, "lines")
        .select("*")
        .eq("transfer_id", transfer_id)
        .order("created_at")
        .execute()
    )
    return _rows(resp)


def create_draft(
    client: Client,
    *,
    actor: str,
    site: str = "SYP",
    from_branch: str = "HQ",
    to_branch: str = "SYP",
) -> dict[str, Any]:
    transfer_id = str(uuid4())
    row = {
        "transfer_id": transfer_id,
        "short_id": make_short_id(transfer_id),
        "status": "draft",
        "site": site,
        "from_branch": from_branch.upper(),
        "to_branch": to_branch.upper(),
        "requested_by": actor,
    }
    resp = _table(client, "requests").insert(row).select("*").execute()
    return _first_row(resp)


def set_request_lines(
    client: Client,
    transfer_id: str,
    lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _table(client, "lines").delete().eq("transfer_id", transfer_id).execute()
    if not lines:
        return []
    rows = []
    for ln in lines:
        qty = float(ln.get("qty_requested") or ln.get("qty") or 0)
        rows.append(
            {
                "line_id": str(uuid4()),
                "transfer_id": transfer_id,
                "bcode": str(ln["bcode"]).strip(),
                "descr": (ln.get("descr") or "").strip() or None,
                "qty_requested": qty,
                "qty_prepared": 0,
                "qty_received": 0,
                "line_status": "open",
            }
        )
    resp = _table(client, "lines").insert(rows).select("*").execute()
    return _rows(resp)


def submit_request(client: Client, transfer_id: str, *, actor: str) -> dict[str, Any]:
    lines = list_lines(client, transfer_id)
    has_shipments = bool(
        _rows(_table(client, "shipments").select("shipment_id").eq("transfer_id", transfer_id).execute())
    )
    status = derive_request_status(header_status="requested", lines=lines, has_shipments=has_shipments)
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": status,
        "requested_at": now,
        "requested_by": actor,
        "updated_at": now,
    }
    resp = (
        _table(client, "requests")
        .update(patch)
        .eq("transfer_id", transfer_id)
        .eq("status", "draft")
        .select("*")
        .execute()
    )
    return _first_row(resp)


def insert_event(
    client: Client,
    *,
    transfer_id: str | None,
    event_type: str,
    actor: str | None = None,
    payload: dict | None = None,
) -> None:
    _table(client, "events").insert(
        {
            "event_id": str(uuid4()),
            "transfer_id": transfer_id,
            "event_type": event_type,
            "actor": actor,
            "payload": payload or {},
        }
    ).execute()


def enrich_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for ln in lines:
        row = dict(ln)
        cancelled = bool(row.get("cancelled_at"))
        row["line_status"] = derive_line_status(
            qty_requested=row.get("qty_requested", 0),
            qty_prepared=row.get("qty_prepared", 0),
            qty_received=row.get("qty_received", 0),
            cancelled=cancelled,
        )
        row["qty_open_prepare"] = max(
            float(row.get("qty_requested") or 0) - float(row.get("qty_prepared") or 0), 0
        )
        row["qty_open_receive"] = max(
            float(row.get("qty_prepared") or 0) - float(row.get("qty_received") or 0), 0
        )
        row["qty_short_order_prepare"] = qty_short_vs_order(
            row.get("qty_requested", 0), row.get("qty_prepared", 0)
        )
        row["qty_short_order_receive"] = qty_short_vs_order(
            row.get("qty_requested", 0), row.get("qty_received", 0)
        )
        row["prep_recv_mismatch"] = prep_recv_mismatch(
            row.get("qty_prepared", 0), row.get("qty_received", 0)
        )
        out.append(row)
    return out


def refresh_request_status(client: Client, transfer_id: str) -> dict[str, Any]:
    header = get_request(client, transfer_id)
    lines = list_lines(client, transfer_id)
    has_shipments = bool(
        _rows(_table(client, "shipments").select("shipment_id").eq("transfer_id", transfer_id).execute())
    )
    status = derive_request_status(
        header_status=header.get("status") or "draft",
        lines=enrich_lines(lines),
        has_shipments=has_shipments,
    )
    patch = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    resp = (
        _table(client, "requests")
        .update(patch)
        .eq("transfer_id", transfer_id)
        .select("*")
        .execute()
    )
    return _first_row(resp)


def create_shipment(
    client: Client, *, transfer_id: str, tf_billno: str, client_token: str
) -> dict[str, Any]:
    """Create a shipment record for tracking."""
    shipment_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "shipment_id": shipment_id,
        "transfer_id": transfer_id,
        "tf_billno": tf_billno,
        "ship_billno": tf_billno,
        "client_token": client_token,
        "created_at": now,
    }
    resp = client.schema(TRANSFER_SCHEMA).from_("shipments").insert(row).select("*").execute()
    return _first_row(resp)


def get_receipt_by_token(client: Client, client_token: str) -> dict[str, Any] | None:
    """Get receive receipt by client token."""
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("receipts")
        .select("*")
        .eq("client_token", client_token)
        .limit(1)
        .execute()
    )
    rows = _rows(resp)
    return rows[0] if rows else None


def create_receipt(
    client: Client,
    *,
    shipment_id: str,
    client_token: str,
    receive_billno: str,
) -> dict[str, Any]:
    row = {
        "receipt_id": str(uuid4()),
        "shipment_id": shipment_id,
        "client_token": client_token,
        "receive_billno": receive_billno,
    }
    resp = client.schema(TRANSFER_SCHEMA).from_("receipts").insert(row).select("*").execute()
    return _first_row(resp)


def shipment_has_lines(client: Client, shipment_id: str) -> bool:
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipment_lines")
        .select("shipment_line_id")
        .eq("shipment_id", shipment_id)
        .limit(1)
        .execute()
    )
    return bool(_rows(resp))


def get_shipment_by_token(client: Client, *, transfer_id: str, client_token: str) -> dict[str, Any] | None:
    """Get shipment by client token."""
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipments")
        .select("*")
        .eq("transfer_id", transfer_id)
        .eq("client_token", client_token)
        .limit(1)
        .execute()
    )
    
    rows = _rows(resp)
    return rows[0] if rows else None


def list_shipments(client: Client, *, transfer_id: str) -> list[dict[str, Any]]:
    """List all shipments for a transfer."""
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipments")
        .select("*")
        .eq("transfer_id", transfer_id)
        .execute()
    )

    return _rows(resp)


def list_shipment_lines(client: Client, *, shipment_id: str) -> list[dict[str, Any]]:
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipment_lines")
        .select("*")
        .eq("shipment_id", shipment_id)
        .execute()
    )
    return _rows(resp)


def add_shipment_lines(client: Client, *, shipment_id: str, lines: list[dict[str, Any]]) -> None:
    """Add lines to a shipment."""
    rows = []
    for line in lines:
        rows.append({
            "shipment_line_id": str(uuid4()),
            "shipment_id": shipment_id,
            "line_id": line.get("line_id"),
            "bcode": str(line.get("bcode") or "").strip(),
            "qty_shipped": float(line.get("qty_ship") or line.get("qty_shipped") or 0),
        })
    if rows:
        client.schema(TRANSFER_SCHEMA).from_("shipment_lines").insert(rows).execute()


def _rpc_bump(client: Client, fn: str, params: dict[str, Any]) -> None:
    try:
        resp = client.schema(TRANSFER_SCHEMA).rpc(fn, params).execute()
    except Exception as exc:
        raise BumpError(str(exc)) from exc
    if not resp.data:
        raise BumpError(f"{fn} failed")


def bump_line_prepared(client: Client, *, line_id: str, qty_ship: float) -> None:
    """Atomically add to prepared quantity for a line."""
    _rpc_bump(
        client,
        "bump_line_prepared",
        {"p_line_id": line_id, "p_qty": float(qty_ship)},
    )


def bump_line_received(client: Client, *, line_id: str, qty_receive: float) -> None:
    """Atomically add to received quantity for a line."""
    _rpc_bump(
        client,
        "bump_line_received",
        {"p_line_id": line_id, "p_qty": float(qty_receive)},
    )


def delete_draft(client: Client, *, transfer_id: str) -> bool:
    """Hard-delete a draft request (lines cascade)."""
    resp = (
        _table(client, "requests")
        .delete()
        .eq("transfer_id", transfer_id)
        .eq("status", "draft")
        .execute()
    )
    return bool(resp.data)


def list_receive_queue(client: Client, *, site: str) -> list[dict[str, Any]]:
    """Flat list of shipment lines ready to receive (HQ/SYP must have prepared first)."""
    site_u = (site or "SYP").upper()
    reqs = list_requests(client, role="receive", site=site_u)
    if not reqs:
        return []
    transfer_ids = [r["transfer_id"] for r in reqs]
    req_by_id = {r["transfer_id"]: r for r in reqs}
    ships_by = list_shipments_by_transfers(client, transfer_ids)
    active_transfer_ids = [tid for tid, ships in ships_by.items() if ships]
    if not active_transfer_ids:
        return []

    lines_by = list_lines_by_transfers(client, active_transfer_ids)
    codes = sorted(
        {
            (ln.get("bcode") or "").strip()
            for tid in active_transfer_ids
            for ln in (lines_by.get(tid) or [])
            if (ln.get("bcode") or "").strip()
        }
    )
    from src.transfer.parts9 import _fetch_dual_icmas

    hq_icmas, syp_icmas = (
        _fetch_dual_icmas(codes, include_blocked=True) if codes else ({}, {})
    )

    enriched_by: dict[str, list[dict[str, Any]]] = {}
    for tid in active_transfer_ids:
        req = req_by_id[tid]
        enriched_by[tid] = enrich_transfer_lines(
            enrich_lines(lines_by.get(tid) or []),
            from_branch=req.get("from_branch"),
            to_branch=req.get("to_branch"),
            hq_icmas=hq_icmas,
            syp_icmas=syp_icmas,
        )

    ship_ids = [s["shipment_id"] for ships in ships_by.values() for s in ships]
    ship_lines_by = list_shipment_lines_by_shipments(client, ship_ids)

    out: list[dict[str, Any]] = []
    for tid in active_transfer_ids:
        req = req_by_id[tid]
        lines_by_id = {
            ln["line_id"]: ln for ln in (enriched_by.get(tid) or []) if ln.get("line_id")
        }
        for ship in ships_by.get(tid) or []:
            ship_billno = ship.get("ship_billno") or ship.get("tf_billno") or ""
            for sl in ship_lines_by.get(ship["shipment_id"]) or []:
                qty_shipped = float(sl.get("qty_shipped") or 0)
                qty_received = float(sl.get("qty_received") or 0)
                qty_open = qty_shipped - qty_received
                if qty_open <= 0:
                    continue
                tr_line = lines_by_id.get(sl.get("line_id"), {})
                out.append(
                    {
                        "shipment_line_id": sl["shipment_line_id"],
                        "shipment_id": ship["shipment_id"],
                        "transfer_id": tid,
                        "short_id": req.get("short_id"),
                        "from_branch": req.get("from_branch"),
                        "to_branch": req.get("to_branch"),
                        "status": req.get("status"),
                        "line_id": sl.get("line_id"),
                        "bcode": sl.get("bcode"),
                        "descr": tr_line.get("descr") or "",
                        "qty_shipped": qty_shipped,
                        "qty_received": qty_received,
                        "qty_open": qty_open,
                        "ship_billno": ship_billno,
                        "iclow_id": tr_line.get("iclow_id"),
                        "hq_qtyoh2": tr_line.get("hq_qtyoh2"),
                        "syp_qtyoh2": tr_line.get("syp_qtyoh2"),
                        "to_qtyoh2": tr_line.get("to_qtyoh2"),
                        "ui1": tr_line.get("ui1"),
                        "ui2": tr_line.get("ui2"),
                        "mtp2": tr_line.get("mtp2"),
                    }
                )
    return out


def bump_shipment_line_received(
    client: Client, *, shipment_line_id: str, qty_receive: float
) -> None:
    """Atomically add to received quantity on a shipment line."""
    _rpc_bump(
        client,
        "bump_shipment_line_received",
        {"p_shipment_line_id": shipment_line_id, "p_qty": float(qty_receive)},
    )


def cancel_request(client: Client, *, transfer_id: str) -> dict[str, Any]:
    """Cancel a transfer request."""
    lines = list_lines(client, transfer_id)
    has_shipments = bool(
        _rows(_table(client, "shipments").select("shipment_id").eq("transfer_id", transfer_id).execute())
    )
    status = derive_request_status(header_status="cancelled", lines=lines, has_shipments=has_shipments)

    patch = {
        "status": status,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = (
        _table(client, "requests")
        .update(patch)
        .eq("transfer_id", transfer_id)
        .select("*")
        .execute()
    )

    return _first_row(resp)
