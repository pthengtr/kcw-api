from __future__ import annotations

import os

from src.stock_check.net import resolve_lan_public_base_url, resolve_tailscale_base_url


def resolve_explorer_public_base_url(*, explicit: str | None = None, port: int | None = None) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("PARTS9_EXPLORER_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="PARTS9_EXPLORER_LISTEN_PORT",
        default_port=8788,
    )


def resolve_explorer_tailscale_base_url(
    *,
    explicit: str | None = None,
    port: int | None = None,
) -> str | None:
    env_explicit = (
        explicit if explicit is not None else os.getenv("PARTS9_EXPLORER_TAILSCALE_BASE_URL")
    )
    return resolve_tailscale_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="PARTS9_EXPLORER_LISTEN_PORT",
        default_port=8788,
    )


def is_tailscale_cg_nat(ip: str | None) -> bool:
    from src.stock_check.net import is_tailscale_cg_nat as _is_ts

    return _is_ts(ip)
