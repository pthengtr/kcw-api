from __future__ import annotations

import os
import socket


def detect_lan_ipv4() -> str | None:
    """Best-effort primary LAN IPv4 (skips loopback)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # No packets sent; OS picks the interface for the default route.
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        finally:
            sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def resolve_lan_public_base_url(
    *,
    explicit: str | None,
    port: int | None,
    env_port_key: str,
    default_port: int,
) -> str | None:
    value = (explicit or "").strip().rstrip("/")
    if value:
        return value
    ip = detect_lan_ipv4()
    if not ip:
        return None
    listen_port = port
    if listen_port is None:
        try:
            listen_port = int(os.getenv(env_port_key) or str(default_port))
        except ValueError:
            listen_port = default_port
    return f"http://{ip}:{listen_port}"


def resolve_stock_check_public_base_url(
    *,
    explicit: str | None = None,
    port: int | None = None,
) -> str | None:
    """
    Prefer STOCK_CHECK_PUBLIC_BASE_URL override; else http://<lan-ip>:<port>.

    Re-call on each heartbeat so DHCP IP changes propagate without restart.
    """
    env_explicit = explicit if explicit is not None else os.getenv("STOCK_CHECK_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="STOCK_CHECK_LISTEN_PORT",
        default_port=8787,
    )


def is_tailscale_cg_nat(ip: str | None) -> bool:
    """True for Tailscale IPv4 CGNAT 100.64.0.0/10 and IPv6 fd7a:115c:a1e0::/48."""
    if not ip:
        return False
    host = ip.split("%")[0].strip().lower()
    if host.startswith("::ffff:"):
        host = host[7:]
    if ":" in host:
        return host.startswith("fd7a:115c:a1e0:")
    parts = host.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return a == 100 and 64 <= b <= 127


def client_ip(request) -> str:
    if getattr(request, "client", None) and request.client.host:
        return request.client.host
    return ""


def resolve_companion_public_base_url(
    *,
    explicit: str | None = None,
    port: int | None = None,
) -> str | None:
    env_explicit = explicit if explicit is not None else os.getenv("COMPANION_PUBLIC_BASE_URL")
    return resolve_lan_public_base_url(
        explicit=env_explicit,
        port=port,
        env_port_key="COMPANION_LISTEN_PORT",
        default_port=8000,
    )
