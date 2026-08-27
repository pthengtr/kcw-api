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
    resp = _table(client, "vendor_bank").insert(row).select("*").single().execute()
    return dict(resp.data or {})


def update_vendor_bank(client: Client, bank_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    resp = (
        _table(client, "vendor_bank")
        .update(patch)
        .eq("bank_id", bank_id)
        .select("*")
        .single()
        .execute()
    )
    return dict(resp.data or {})


def get_vendor_bank(client: Client, bank_id: str) -> dict[str, Any] | None:
    resp = _table(client, "vendor_bank").select("*").eq("bank_id", bank_id).maybe_single().execute()
    return dict(resp.data) if resp.data else None


def insert_reminder(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "reminder").insert(row).select("*").single().execute()
    return dict(resp.data or {})


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
        .single()
        .execute()
    )
    return dict(resp.data or {})


def list_reminders(client: Client) -> list[dict[str, Any]]:
    resp = (
        _table(client, "reminder")
        .select("*, vendor_bank(*)")
        .order("due_date")
        .execute()
    )
    return list(resp.data or [])
