from __future__ import annotations

import os

from src.stock_check.net import resolve_lan_public_base_url


def resolve_explorer_public_base_url(*, explicit: str | None = None, port: int | None = None) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("PARTS9_EXPLORER_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="PARTS9_EXPLORER_LISTEN_PORT",
        default_port=8788,
    )


def is_tailscale_cg_nat(ip: str | None) -> bool:
    """True for Tailscale IPv4 CGNAT 100.64.0.0/10 and IPv6 fd7a:115c:a1e0::/48."""
    if not ip:
        return False
    host = ip.split("%")[0].strip().lower()
    if host.startswith("::ffff:"):
        host = host[7:]
    if ":" in host:
        h = host.replace("::", ":")
        return host.startswith("fd7a:115c:a1e0:") or host.startswith("fd7a:115c:a1e0::")
    parts = host.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return a == 100 and 64 <= b <= 127
