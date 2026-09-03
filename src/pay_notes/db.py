from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from src.pay_notes.config import get_pay_notes_settings

PAY_NOTE_SCHEMA = "pay_note"


@lru_cache
def get_pay_notes_supabase_client() -> Client:
    settings = get_pay_notes_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(PAY_NOTE_SCHEMA).from_(name)


def _first_row(resp) -> dict[str, Any]:
    """supabase-py 2.x: insert/update().select() returns a list, not .single()."""
    data = resp.data
    if data is None:
        return {}
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data)


def list_vendor_banks(client: Client, acctno: str) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    resp = (
        _table(client, "vendor_bank")
        .select("*")
        .eq("acctno", acct)
        .order("is_default", desc=True)
        .order("bank_name")
        .execute()
    )
    return list(resp.data or [])


def insert_vendor_bank(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "vendor_bank").insert(row).select("*").execute()
    return _first_row(resp)


def update_vendor_bank(client: Client, bank_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    resp = (
        _table(client, "vendor_bank")
        .update(patch)
        .eq("bank_id", bank_id)
        .select("*")
        .execute()
    )
    return _first_row(resp)


def get_vendor_bank(client: Client, bank_id: str) -> dict[str, Any] | None:
    resp = _table(client, "vendor_bank").select("*").eq("bank_id", bank_id).maybe_single().execute()
    if not resp or not resp.data:
        return None
    return dict(resp.data)


def get_reminder(client: Client, acctno: str, noteno: str) -> dict[str, Any] | None:
    resp = (
        _table(client, "reminder")
        .select("*")
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .maybe_single()
        .execute()
    )
    if not resp or not resp.data:
        return None
    return dict(resp.data)


def insert_reminder(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "reminder").insert(row).select("*").execute()
    return _first_row(resp)


def patch_reminder(
    client: Client,
    acctno: str,
    noteno: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    resp = (
        _table(client, "reminder")
        .update(patch)
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .select("*")
        .execute()
    )
    return _first_row(resp)


def delete_reminder(client: Client, acctno: str, noteno: str) -> bool:
    """Remove pay_note.reminder for a canceled unpaid note. Returns True if a row was deleted."""
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return False
    before = get_reminder(client, acct, note)
    if not before:
        return False
    (
        _table(client, "reminder")
        .delete()
        .eq("acctno", acct)
        .eq("noteno", note)
        .execute()
    )
    return True


def rename_reminder(
    client: Client,
    acctno: str,
    from_noteno: str,
    to_noteno: str,
) -> dict[str, Any] | None:
    """Change reminder PK noteno (acctno, noteno) when KSS gains _N suffix."""
    acct = acctno.strip()
    src = from_noteno.strip()
    dst = to_noteno.strip()
    if not acct or not src or not dst or src == dst:
        return None
    row = get_reminder(client, acct, src)
    if not row:
        return None
    new_row = {k: v for k, v in row.items() if k not in ("created_at", "updated_at")}
    new_row["noteno"] = dst
    (
        _table(client, "reminder")
        .delete()
        .eq("acctno", acct)
        .eq("noteno", src)
        .execute()
    )
    return insert_reminder(client, new_row)


def list_reminders(client: Client) -> list[dict[str, Any]]:
    resp = (
        _table(client, "reminder")
        .select("*, vendor_bank(*)")
        .order("due_date")
        .execute()
    )
    return list(resp.data or [])
