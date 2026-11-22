from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from src.receive_notes.config import get_receive_notes_settings

RECEIVE_NOTE_SCHEMA = "receive_note"
_BKK = ZoneInfo("Asia/Bangkok")


@lru_cache
def get_receive_notes_supabase_client() -> Client:
    settings = get_receive_notes_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(RECEIVE_NOTE_SCHEMA).from_(name)


def _first_row(resp) -> dict[str, Any]:
    data = resp.data
    if data is None:
        return {}
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data)


def insert_note(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "note").insert(row).select("*").execute()
    return _first_row(resp)


def is_duplicate_note_key_error(exc: BaseException) -> bool:
    """PostgREST / Postgres unique violation on receive_note.note PK."""
    text = str(exc).lower()
    code = str(getattr(exc, "code", "") or "").lower()
    if code == "23505" or "23505" in text:
        return True
    return "duplicate key" in text or "note_pkey" in text


class NoteOverlayConflict(RuntimeError):
    """Overlay row exists in a terminal state and must not be reopened."""

    def __init__(self, message: str, *, code: str = "overlay_conflict"):
        super().__init__(message)
        self.code = code


def ensure_open_note(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    """Insert overlay note, or reactivate/refresh when (acctno, noteno) already exists.

    Matches docs/receive-notes.md "Upsert overlay". Canceled (and orphan open)
    rows are reopened so BN/BNN reuse after soft-cancel / double-submit does not
    500 with note_pkey. Received overlays stay blocked.
    """
    acct = str(row.get("acctno") or "").strip()
    note = str(row.get("noteno") or "").strip()
    if not acct or not note:
        raise ValueError("acctno and noteno required")

    def _refresh(existing: dict[str, Any]) -> dict[str, Any]:
        status = str(existing.get("status") or "").lower()
        if status == "received":
            raise NoteOverlayConflict(
                f"note overlay already received for {acct}/{note}",
                code="already_received",
            )
        patch = {
            key: value
            for key, value in row.items()
            if key not in ("acctno", "noteno", "created_at", "created_by")
        }
        patch["status"] = "open"
        return patch_note(client, acct, note, patch)

    existing = get_note(client, acct, note)
    if existing:
        return _refresh(existing)
    try:
        return insert_note(client, row)
    except Exception as exc:
        # Concurrent create-and-pay: loser hit note_pkey after winner inserted.
        if not is_duplicate_note_key_error(exc):
            raise
        existing = get_note(client, acct, note)
        if not existing:
            raise
        return _refresh(existing)


def patch_note(client: Client, acctno: str, noteno: str, patch: dict[str, Any]) -> dict[str, Any]:
    patch = {**patch, "updated_at": datetime.now(_BKK).isoformat()}
    resp = (
        _table(client, "note")
        .update(patch)
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .select("*")
        .execute()
    )
    return _first_row(resp)


def get_note(client: Client, acctno: str, noteno: str) -> dict[str, Any] | None:
    resp = (
        _table(client, "note")
        .select("*")
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .maybe_single()
        .execute()
    )
    if not resp or not resp.data:
        return None
    return dict(resp.data)


def list_notes(client: Client, *, status: str | None = None) -> list[dict[str, Any]]:
    q = _table(client, "note").select("*").order("due_date").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    resp = q.execute()
    return list(resp.data or [])


def delete_note(client: Client, acctno: str, noteno: str) -> None:
    (
        _table(client, "note")
        .delete()
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .execute()
    )


def list_open_notes(client: Client) -> list[dict[str, Any]]:
    """Overlay rows for pending board (status=open)."""
    return list_notes(client, status="open")


def list_canceled_service_notes(client: Client) -> list[dict[str, Any]]:
    """Soft-canceled billing notes kept for audit / red status display."""
    return list_notes(client, status="canceled")


def list_all_service_notes(client: Client) -> list[dict[str, Any]]:
    """All overlay notes including received/canceled — for vouchered merge."""
    return list_notes(client, status=None)


def insert_receipt(client: Client, row: dict[str, Any]) -> dict[str, Any]:
    resp = _table(client, "receipt").insert(row).select("*").execute()
    return _first_row(resp)


def patch_receipt(client: Client, receipt_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    patch = {**patch, "updated_at": datetime.now(_BKK).isoformat()}
    resp = (
        _table(client, "receipt")
        .update(patch)
        .eq("id", receipt_id)
        .select("*")
        .execute()
    )
    return _first_row(resp)


def get_receipt(client: Client, receipt_id: str) -> dict[str, Any] | None:
    resp = (
        _table(client, "receipt")
        .select("*, receipt_bill(*), receipt_channel(*)")
        .eq("id", receipt_id)
        .maybe_single()
        .execute()
    )
    if not resp or not resp.data:
        return None
    return dict(resp.data)


def get_receipt_by_voucno(client: Client, voucno: str) -> dict[str, Any] | None:
    resp = (
        _table(client, "receipt")
        .select("*, receipt_bill(*), receipt_channel(*)")
        .eq("voucno", voucno.strip())
        .maybe_single()
        .execute()
    )
    if not resp or not resp.data:
        return None
    return dict(resp.data)


def get_pending_tiger_receipt_for_note(
    client: Client, acctno: str, noteno: str
) -> dict[str, Any] | None:
    """Latest overlay receipt awaiting Tiger for this billing note (if any)."""
    resp = (
        _table(client, "receipt")
        .select("*, receipt_bill(*), receipt_channel(*)")
        .eq("acctno", acctno.strip())
        .eq("noteno", noteno.strip())
        .eq("workflow_status", "awaiting_tiger")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = list(resp.data or [])
    return dict(rows[0]) if rows else None


def list_receipts(
    client: Client,
    *,
    workflow_status: str | None = None,
    received_at: str | None = None,
    acctno: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    q = (
        _table(client, "receipt")
        .select("*, receipt_bill(*), receipt_channel(*)")
        .order("received_at", desc=True)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if workflow_status:
        q = q.eq("workflow_status", workflow_status)
    if received_at:
        q = q.eq("received_at", received_at)
    if acctno:
        q = q.eq("acctno", acctno.strip())
    resp = q.execute()
    return list(resp.data or [])


def list_review_queue(client: Client, *, limit: int = 200) -> list[dict[str, Any]]:
    resp = (
        _table(client, "receipt")
        .select("*, receipt_bill(*), receipt_channel(*)")
        .in_("workflow_status", ["awaiting_proof", "awaiting_tiger", "review", "failed"])
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(resp.data or [])


def insert_receipt_bills(client: Client, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    resp = _table(client, "receipt_bill").insert(rows).select("*").execute()
    return list(resp.data or [])


def insert_receipt_channels(client: Client, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    resp = _table(client, "receipt_channel").insert(rows).select("*").execute()
    return list(resp.data or [])


def prior_allocations_for_bills(client: Client, billnos: list[str]) -> dict[str, float]:
    """Sum allocate_amt for bills on non-failed receipts (partial-pay remainder)."""
    nums = [b.strip() for b in billnos if (b or "").strip()]
    if not nums:
        return {}
    resp = (
        _table(client, "receipt_bill")
        .select(
            "billno, allocate_amt, "
            "receipt:receipt_id(workflow_status, money_confirmed)"
        )
        .in_("billno", nums)
        .execute()
    )
    totals: dict[str, float] = {n: 0.0 for n in nums}
    for row in resp.data or []:
        receipt = row.get("receipt") or {}
        status = str(receipt.get("workflow_status") or "")
        # Skip failed / unconfirmed Tiger so a cancelled cash attempt can retry.
        if status in ("failed", "awaiting_tiger"):
            continue
        if status == "review" and not receipt.get("money_confirmed"):
            continue
        bno = str(row.get("billno") or "").strip()
        totals[bno] = round(totals.get(bno, 0.0) + float(row.get("allocate_amt") or 0), 2)
    return totals


def daily_channel_totals(client: Client, received_at: str) -> dict[str, Any]:
    day = (received_at or date.today().isoformat()).strip()
    rows = list_receipts(client, received_at=day, limit=500)
    totals = {
        "received_at": day,
        "count": 0,
        "netamt": 0.0,
        "cash_tiger": 0.0,
        "cash_manual": 0.0,
        "transfer": 0.0,
        "cheque": 0.0,
    }
    for row in rows:
        if str(row.get("workflow_status") or "") in ("failed", "awaiting_tiger"):
            continue
        if str(row.get("kss_sync_status") or "") == "failed" and not row.get("voucno"):
            continue
        totals["count"] += 1
        totals["netamt"] = round(totals["netamt"] + float(row.get("netamt") or 0), 2)
        cash = float(row.get("cash_amt") or 0)
        if cash > 0:
            if str(row.get("cash_mode") or "") == "manual":
                totals["cash_manual"] = round(totals["cash_manual"] + cash, 2)
            else:
                totals["cash_tiger"] = round(totals["cash_tiger"] + cash, 2)
        totals["transfer"] = round(totals["transfer"] + float(row.get("transfer_amt") or 0), 2)
        totals["cheque"] = round(totals["cheque"] + float(row.get("cheque_amt") or 0), 2)
    return totals
