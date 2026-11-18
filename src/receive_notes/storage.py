from __future__ import annotations

from typing import Any

from src.pay_notes.storage import (
    list_folder,
    public_url as _pay_public_url,
    remove_paths,
    safe_storage_filename,
    safe_storage_segment,
    upload_bytes as _pay_upload_bytes,
)
from src.receive_notes.config import get_receive_notes_settings


def bill_image_prefix(acctno: str, noteno: str) -> str:
    acct = safe_storage_segment(acctno, default="acct")
    note = safe_storage_segment(noteno, default="note")
    return f"public/receive_note/bill/{acct}/{note}"


def payment_image_prefix(voucno: str) -> str:
    return f"public/receive_note/payment/{safe_storage_segment(voucno, default='vouc')}"


def receipt_image_prefix(receipt_id: str) -> str:
    return f"public/receive_note/receipt/{safe_storage_segment(receipt_id, default='rcpt')}"


def public_url(path: str) -> str | None:
    settings = get_receive_notes_settings()
    root = (settings.supabase_url or "").rstrip("/")
    bucket = settings.supabase_image_bucket or "pictures"
    if not root:
        return None
    clean = (path or "").lstrip("/")
    return f"{root}/storage/v1/object/public/{bucket}/{clean}"


def upload_bytes(client, *, path: str, data: bytes, content_type: str | None = None) -> str:
    settings = get_receive_notes_settings()
    bucket = settings.supabase_image_bucket or "pictures"
    client.storage.from_(bucket).upload(
        path=path.lstrip("/"),
        file=data,
        file_options={
            "content-type": content_type or "application/octet-stream",
            "upsert": "true",
        },
    )
    return path.lstrip("/")


__all__ = [
    "bill_image_prefix",
    "payment_image_prefix",
    "receipt_image_prefix",
    "public_url",
    "list_folder",
    "remove_paths",
    "safe_storage_filename",
    "safe_storage_segment",
    "upload_bytes",
    "_pay_public_url",
    "_pay_upload_bytes",
]
