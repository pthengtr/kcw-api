from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from src.transfer.config import get_transfer_settings
from datetime import datetime, timezone

from src.transfer.state import derive_line_status, derive_request_status, make_short_id

TRANSFER_SCHEMA = "transfer"


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


def list_requests(client: Client, *, status: str | None = None) -> list[dict[str, Any]]:
    q = _table(client, "requests").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    return _rows(q.execute())


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


def create_draft(client: Client, *, actor: str, site: str = "SYP") -> dict[str, Any]:
    transfer_id = str(uuid4())
    row = {
        "transfer_id": transfer_id,
        "short_id": make_short_id(transfer_id),
        "status": "draft",
        "site": site,
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
        out.append(row)
    return out


def create_shipment(client: Client, *, transfer_id: str, tf_billno: str, client_token: str) -> dict[str, Any]:
    """Create a shipment record for tracking."""
    from uuid import uuid4
    
    shipment_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    row = {
        "shipment_id": shipment_id,
        "transfer_id": transfer_id,
        "tf_billno": tf_billno,
        "client_token": client_token,
        "status": "prepared",
        "created_at": now,
    }
    
    resp = client.schema(TRANSFER_SCHEMA).from_("shipments").insert(row).select("*").execute()
    return _first_row(resp)


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


def add_shipment_lines(client: Client, *, shipment_id: str, lines: list[dict[str, Any]]) -> None:
    """Add lines to a shipment."""
    from uuid import uuid4
    rows = []
    for line in lines:
        rows.append({
            "shipment_line_id": str(uuid4()),
            "shipment_id": shipment_id,
            "line_id": line.get("line_id"),
            "bcode": str(line.get("bcode") or "").strip(),
            "qty_ship": float(line.get("qty_ship") or 0),
            "descr": (line.get("descr") or "").strip() or None
        })
    
    if rows:
        client.schema(TRANSFER_SCHEMA).from_("shipment_lines").insert(rows).execute()


def bump_line_prepared(client: Client, *, line_id: str, qty_ship: float) -> None:
    """Update prepared quantity for a line."""
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("lines")
        .update({
            "qty_prepared": float(qty_ship),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("line_id", line_id)
        .select("*")
        .execute()
    )


def bump_line_received(client: Client, *, line_id: str, qty_receive: float) -> None:
    """Update received quantity for a line."""
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("lines") 
        .update({
            "qty_received": float(qty_receive),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("line_id", line_id)
        .select("*")
        .execute()
    )


def cancel_request(client: Client, *, transfer_id: str) -> dict[str, Any]:
    """Cancel a transfer request."""
    from src.transfer.state import derive_request_status
    
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
