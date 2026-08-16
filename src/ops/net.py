from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

from src.stock_check.net import resolve_lan_public_base_url, resolve_tailscale_base_url


def resolve_ops_public_base_url(*, explicit: str | None = None, port: int | None = None) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("KCW_OPS_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="KCW_OPS_LISTEN_PORT",
        default_port=8790,
    )


def resolve_ops_tailscale_base_url(
    *,
    explicit: str | None = None,
    port: int | None = None,
) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("KCW_OPS_TAILSCALE_BASE_URL")
    return resolve_tailscale_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="KCW_OPS_LISTEN_PORT",
        default_port=8790,
    )


def is_tailscale_cg_nat(ip: str | None) -> bool:
    from src.stock_check.net import is_tailscale_cg_nat as _is_ts

    return _is_ts(ip)


def rewrite_base_port(url: str | None, port: int) -> str | None:
    """Turn explorer :8788 URLs into ops :8790 without a new heartbeat column."""
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
