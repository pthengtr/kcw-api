from __future__ import annotations

import os
import re
from pathlib import Path

from supabase import Client, create_client


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def get_supabase_client() -> Client:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def staging_dir(ticket_id: str) -> Path:
    root = Path(
        os.getenv(
            "SUPPORT_ATTACHMENTS_DIR",
            "/home/hqadmin/projects/.support-attachments",
        )
    )
    path = root / ticket_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(index: int, storage_path: str) -> str:
    base = storage_path.rsplit("/", 1)[-1] or f"file-{index}"
    base = _UNSAFE.sub("_", base).strip("._-") or f"file-{index}"
    return f"{index:02d}-{base}"


def download_attachments(
    client: Client,
    *,
    ticket_id: str,
    storage_paths: list[str],
    bucket: str = "pictures",
) -> list[Path]:
    dest = staging_dir(ticket_id)
    out: list[Path] = []
    for i, raw in enumerate(storage_paths or [], start=1):
        path = (raw or "").lstrip("/")
        if not path:
            continue
        data = client.storage.from_(bucket).download(path)
        if data is None:
            raise RuntimeError(f"Failed to download attachment: {path}")
        local = dest / _safe_name(i, path)
        local.write_bytes(data)
        if local.stat().st_size > 15 * 1024 * 1024:
            local.unlink(missing_ok=True)
            raise RuntimeError(f"Attachment too large (>15MB): {path}")
        out.append(local)
    return out


def cleanup_attachments(ticket_id: str) -> None:
    dest = staging_dir(ticket_id)
    if not dest.exists():
        return
    for child in dest.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)
    try:
        dest.rmdir()
    except OSError:
        pass
