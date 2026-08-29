from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

from src.stock_check.net import resolve_lan_public_base_url, resolve_tailscale_base_url


def resolve_transfer_public_base_url(*, explicit: str | None = None, port: int | None = None) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("TRANSFER_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="TRANSFER_LISTEN_PORT",
        default_port=8792,
    )


def resolve_transfer_tailscale_base_url(
    *,
    explicit: str | None = None,
    port: int | None = None,
) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("TRANSFER_TAILSCALE_BASE_URL")
    return resolve_tailscale_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="TRANSFER_LISTEN_PORT",
        default_port=8792,
    )


def rewrite_base_port(url: str | None, port: int) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    host = parts.hostname or ""
    if not host:
        return None
    netloc = f"{host}:{port}"
    if parts.username:
        user = parts.username
        if parts.password:
            user = f"{user}:{parts.password}"
        netloc = f"{user}@{netloc}"
    return urlunsplit((parts.scheme or "http", netloc, "", "", ""))
