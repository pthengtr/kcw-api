from __future__ import annotations

from typing import Any

from src.pay_notes.config import get_pay_notes_settings


def bill_image_prefix(acctno: str, noteno: str) -> str:
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    return f"public/pay_note/bill/{acct}/{note}"


def payment_image_prefix(voucno: str) -> str:
    return f"public/pay_note/payment/{(voucno or '').strip()}"


def public_url(path: str) -> str | None:
    settings = get_pay_notes_settings()
    root = (settings.supabase_url or "").rstrip("/")
    bucket = settings.supabase_image_bucket or "pictures"
    if not root:
        return None
    clean = (path or "").lstrip("/")
    return f"{root}/storage/v1/object/public/{bucket}/{clean}"


def list_folder(client, prefix: str) -> list[dict[str, Any]]:
    settings = get_pay_notes_settings()
    bucket = settings.supabase_image_bucket or "pictures"
    folder = (prefix or "").strip("/")
    try:
        items = client.storage.from_(bucket).list(folder)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for item in items or []:
        name = (item.get("name") if isinstance(item, dict) else None) or ""
        if not name or name.endswith("/"):
            continue
        rel = f"{folder}/{name}" if folder else name
        url = public_url(rel)
        out.append({"name": name, "path": rel, "url": url})
    return out


def upload_bytes(client, path: str, data: bytes, *, content_type: str = "image/jpeg") -> str:
    settings = get_pay_notes_settings()
    bucket = settings.supabase_image_bucket or "pictures"
    clean = (path or "").lstrip("/")
    opts = {"content-type": content_type, "cache-control": "3600", "upsert": "true"}
    try:
        client.storage.from_(bucket).upload(clean, data, file_options=opts)
    except Exception:
        try:
            client.storage.from_(bucket).remove([clean])
        except Exception:
            pass
        client.storage.from_(bucket).upload(
            clean,
            data,
            file_options={"content-type": content_type, "cache-control": "3600"},
        )
    return clean


def relocate_bill_images(client, acctno: str, from_noteno: str, to_noteno: str) -> list[str]:
    """Move bill images when KSS NOTENO gains an auto suffix (_1)."""
    src = from_noteno.strip()
    dst = to_noteno.strip()
    if not src or not dst or src == dst:
        return []
    settings = get_pay_notes_settings()
    bucket = settings.supabase_image_bucket or "pictures"
    src_prefix = bill_image_prefix(acctno, src).strip("/")
    dst_prefix = bill_image_prefix(acctno, dst).strip("/")
    moved: list[str] = []
    for item in list_folder(client, src_prefix):
        name = (item.get("name") or "").strip()
        if not name:
            continue
        src_path = f"{src_prefix}/{name}"
        dst_path = f"{dst_prefix}/{name}"
        try:
            data = client.storage.from_(bucket).download(src_path)
        except Exception:
            continue
        content_type = "application/octet-stream"
        if name.lower().endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif name.lower().endswith(".png"):
            content_type = "image/png"
        elif name.lower().endswith(".pdf"):
            content_type = "application/pdf"
        upload_bytes(client, dst_path, data, content_type=content_type)
        try:
            client.storage.from_(bucket).remove([src_path])
        except Exception:
            pass
        moved.append(dst_path)
    return moved
