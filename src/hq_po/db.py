from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from src.hq_po.config import get_hq_po_settings
from src.hq_po.guards import HqPoError

SCHEMA = "hq_po"


@lru_cache
def get_hq_po_supabase_client() -> Client:
    settings = get_hq_po_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HqPoError("supabase_missing", "ยังไม่ได้ตั้ง Supabase สำหรับใบสั่งซื้อ")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(SCHEMA).from_(name)


def _rows(resp) -> list[dict[str, Any]]:
    return [dict(row) for row in (resp.data or [])]


def _first(resp) -> dict[str, Any]:
    data = resp.data
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    if isinstance(data, dict):
        return dict(data)
    return {}


def insert_order(
    client: Client,
    *,
    short_id: str,
    docno: str,
    vendor_acctno: str,
    vendor_name: str | None,
    ordered_by: str | None,
    lines: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    header = _first(
        _table(client, "orders")
        .insert(
            {
                "short_id": short_id,
                "docno": docno,
                "vendor_acctno": vendor_acctno,
                "vendor_name": vendor_name,
                "status": "ordered",
                "ordered_by": ordered_by,
                "ordered_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    order_id = header.get("order_id")
    if not order_id:
        raise HqPoError("supabase_write", "บันทึกหัวใบสั่งซื้อไม่สำเร็จ")
    payload = []
    for line in lines:
        payload.append(
            {
                "order_id": order_id,
                "iclow_id": int(line["iclow_id"]),
                "bcode": line["bcode"],
                "descr": line.get("descr"),
                "qty": line["qty"],
                "ui": line.get("ui"),
                "propose_meta": line.get("propose_meta"),
            }
        )
    try:
        stored = _rows(_table(client, "lines").insert(payload).execute())
    except Exception:
        _table(client, "orders").delete().eq("order_id", order_id).execute()
        raise
    if len(stored) != len(payload):
        _table(client, "orders").delete().eq("order_id", order_id).execute()
        raise HqPoError("supabase_write", "บันทึกรายการใบสั่งซื้อไม่ครบ")
    header["lines"] = stored
    return header


def mark_order_canceled(client: Client, order_id: str, *, reason: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    _table(client, "lines").update({"canceled_at": now}).eq("order_id", order_id).is_(
        "canceled_at", "null"
    ).execute()
    _table(client, "orders").update(
        {
            "status": "canceled",
            "canceled_at": now,
            "cancel_reason": (reason or "")[:300] or None,
            "updated_at": now,
        }
    ).eq("order_id", order_id).execute()


def get_order(client: Client, order_id: str) -> dict[str, Any] | None:
    header = _first(
        _table(client, "orders").select("*").eq("order_id", order_id).limit(1).execute()
    )
    if not header:
        return None
    header["lines"] = _rows(
        _table(client, "lines").select("*").eq("order_id", order_id).order("bcode").execute()
    )
    return header


def list_orders(client: Client, *, limit: int = 80) -> list[dict[str, Any]]:
    lim = max(1, min(int(limit or 80), 200))
    headers = _rows(
        _table(client, "orders")
        .select("*")
        .eq("status", "ordered")
        .order("ordered_at", desc=True)
        .limit(lim)
        .execute()
    )
    if not headers:
        return []
    ids = [row["order_id"] for row in headers if row.get("order_id")]
    lines = _rows(
        _table(client, "lines").select("*").in_("order_id", ids).is_("canceled_at", "null").execute()
    )
    by_order: dict[str, list[dict[str, Any]]] = {order_id: [] for order_id in ids}
    for line in lines:
        parent = line.get("order_id")
        if parent in by_order:
            by_order[parent].append(line)
    for header in headers:
        header["lines"] = by_order.get(header.get("order_id"), [])
    return headers
