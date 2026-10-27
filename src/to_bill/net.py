from __future__ import annotations


def is_private_lan(ip: str | None) -> bool:
    """Office LAN and loopback. Tailscale CGNAT is handled separately."""
    if not ip:
        return False
    host = ip.split("%")[0].strip().lower()
    if host.startswith("::ffff:"):
        host = host[7:]
    if host in {"127.0.0.1", "::1"}:
        return True
    if ":" in host:
        return False
    parts = host.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 10:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    return False
