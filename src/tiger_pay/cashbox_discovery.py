"""Discover Tiger Pay cashbox IP by MAC when DHCP moves the device."""

from __future__ import annotations

import concurrent.futures
import logging
import os
import re
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from src.stock_check.net import detect_lan_ipv4
from src.tiger_pay.config import (
    ENV_FILE,
    TigerPaySettings,
    clear_tiger_pay_settings_cache,
    get_tiger_pay_settings,
    persist_tiger_pay_api_host,
)
from src.tiger_pay.mac_addr import normalize_mac

logger = logging.getLogger("kcw.tiger_pay.cashbox_discovery")

_NEIGH_IP_MAC_RE = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3})\s+.*\slladdr\s+([0-9a-f:]{11,17})\b",
    re.IGNORECASE,
)

_rediscover_lock = threading.Lock()
_last_rediscover_attempt_at = 0.0


def parse_api_host(api_host: str) -> tuple[str, str, int]:
    """Return ``(scheme, hostname, port)`` from a Tiger Pay API host URL."""
    host = (api_host or "").strip()
    if not host:
        raise ValueError("TIGER_PAY_API_HOST is empty")
    parsed = urlparse(host if "://" in host else f"http://{host}")
    hostname = (parsed.hostname or "").strip()
    if not hostname:
        raise ValueError(f"TIGER_PAY_API_HOST has no hostname: {api_host!r}")
    scheme = (parsed.scheme or "http").lower()
    if parsed.port is not None:
        port = int(parsed.port)
    elif scheme == "https":
        port = 443
    else:
        port = 80
    return scheme, hostname, port


def build_api_host(*, scheme: str, ip: str, port: int) -> str:
    scheme = (scheme or "http").strip().lower() or "http"
    ip = ip.strip()
    if scheme == "http" and port == 80:
        return f"http://{ip}/"
    if scheme == "https" and port == 443:
        return f"https://{ip}/"
    return f"{scheme}://{ip}:{int(port)}/"


def _ipv4_prefix24(ip: str) -> str | None:
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return None
    try:
        if not all(0 <= int(p) <= 255 for p in parts):
            return None
    except ValueError:
        return None
    return ".".join(parts[:3])


def _read_neighbor_table() -> dict[str, str]:
    """Map normalized MAC → IPv4 from ``ip neigh`` and ``/proc/net/arp``."""
    found: dict[str, str] = {}

    try:
        out = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in (out.stdout or "").splitlines():
            match = _NEIGH_IP_MAC_RE.match(line.strip())
            if not match:
                continue
            ip, mac = match.group(1), match.group(2)
            if "FAILED" in line.upper() or "INCOMPLETE" in line.upper():
                continue
            try:
                found[normalize_mac(mac)] = ip
            except ValueError:
                continue
    except (OSError, subprocess.SubprocessError):
        logger.debug("ip neigh read failed", exc_info=True)

    try:
        arp_text = Path("/proc/net/arp").read_text(encoding="utf-8", errors="replace")
    except OSError:
        arp_text = ""
    for line in arp_text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        ip, mac = parts[0], parts[3]
        if mac == "00:00:00:00:00:00":
            continue
        try:
            found.setdefault(normalize_mac(mac), ip)
        except ValueError:
            continue

    return found


def _ping_host(ip: str, *, timeout_seconds: float = 0.4) -> None:
    if os.name == "nt":
        wait_ms = max(1, int(timeout_seconds * 1000))
        cmd = ["ping", "-n", "1", "-w", str(wait_ms), ip]
    else:
        # -W is seconds on Linux ping; keep small for sweeps.
        wait_s = max(1, int(round(timeout_seconds)))
        cmd = ["ping", "-c", "1", "-W", str(wait_s), ip]
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_seconds + 1.5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _sweep_subnet(prefix24: str, *, max_workers: int = 64) -> None:
    targets = [f"{prefix24}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(_ping_host, targets))


def tcp_port_open(ip: str, port: int, *, timeout_seconds: float = 1.0) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def find_ip_by_mac(
    mac: str,
    *,
    subnet_hints: list[str] | None = None,
    api_port: int | None = None,
    sweep: bool = True,
) -> str | None:
    """
    Locate IPv4 for ``mac``.

    Checks the neighbor/ARP table first, optionally ping-sweeps /24 hints,
    then re-reads neighbors. When ``api_port`` is set, prefer an IP with that
    TCP port open.
    """
    wanted = normalize_mac(mac)
    neighbors = _read_neighbor_table()
    candidate = neighbors.get(wanted)

    if candidate is None and sweep:
        prefixes: list[str] = []
        for hint in subnet_hints or []:
            prefix = _ipv4_prefix24(hint)
            if prefix and prefix not in prefixes:
                prefixes.append(prefix)
        lan = detect_lan_ipv4()
        if lan:
            prefix = _ipv4_prefix24(lan)
            if prefix and prefix not in prefixes:
                prefixes.append(prefix)
        for prefix in prefixes:
            logger.info("Cashbox MAC scan sweeping %s.0/24 for %s", prefix, wanted)
            _sweep_subnet(prefix)
        neighbors = _read_neighbor_table()
        candidate = neighbors.get(wanted)

    if not candidate:
        return None

    if api_port is not None and not tcp_port_open(candidate, api_port):
        # Rare: stale ARP. Keep candidate anyway if nothing else; caller may still try.
        logger.warning(
            "Cashbox MAC %s resolved to %s but TCP :%s is closed",
            wanted,
            candidate,
            api_port,
        )
    return candidate


def _clear_open_api_client_cache() -> None:
    # Local import avoids circular dependency at module load.
    from src.tiger_pay.open_api import get_open_api_client

    get_open_api_client.cache_clear()


def maybe_rediscover_cashbox_api_host(
    *,
    settings: TigerPaySettings | None = None,
    force: bool = False,
) -> str | None:
    """
    On cashbox connect loss, find the device by MAC and update ``TIGER_PAY_API_HOST``.

    Returns the new host URL when updated, else None.
    """
    global _last_rediscover_attempt_at

    cfg = settings or get_tiger_pay_settings()
    mac_raw = (cfg.tiger_pay_cashbox_mac or "").strip()
    if not mac_raw:
        return None

    try:
        mac = normalize_mac(mac_raw)
    except ValueError:
        logger.warning("Invalid TIGER_PAY_CASHBOX_MAC=%r; skipping rediscovery", mac_raw)
        return None

    cooldown = float(cfg.tiger_pay_cashbox_rediscover_cooldown_seconds)
    now = time.monotonic()
    with _rediscover_lock:
        if not force and (now - _last_rediscover_attempt_at) < cooldown:
            return None
        _last_rediscover_attempt_at = now

        try:
            scheme, current_host, port = parse_api_host(cfg.tiger_pay_api_host)
        except ValueError as exc:
            logger.warning("Cannot rediscover cashbox: %s", exc)
            return None

        found_ip = find_ip_by_mac(
            mac,
            subnet_hints=[current_host],
            api_port=port,
            sweep=True,
        )
        if not found_ip:
            logger.warning("Cashbox MAC %s not found on LAN", mac)
            return None

        if found_ip == current_host:
            logger.info(
                "Cashbox MAC %s still at %s; host unchanged",
                mac,
                found_ip,
            )
            return None

        if not tcp_port_open(found_ip, port, timeout_seconds=2.0):
            logger.warning(
                "Cashbox MAC %s at %s but port %s not open; refusing host update",
                mac,
                found_ip,
                port,
            )
            return None

        new_host = build_api_host(scheme=scheme, ip=found_ip, port=port)
        persist_tiger_pay_api_host(new_host, env_file=ENV_FILE)
        clear_tiger_pay_settings_cache()
        _clear_open_api_client_cache()
        logger.warning(
            "Cashbox rediscovered by MAC %s: %s -> %s (updated %s)",
            mac,
            cfg.tiger_pay_api_host,
            new_host,
            ENV_FILE,
        )
        return new_host
