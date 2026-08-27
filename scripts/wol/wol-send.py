#!/usr/bin/env python3
"""Send Wake-on-LAN magic packets (UDP broadcast, port 9)."""

from __future__ import annotations

import argparse
import re
import socket
import sys
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config/kcw/wol-hosts.conf"
DEFAULT_BROADCAST = "192.168.1.255"
DEFAULT_PORT = 9


def normalize_mac(mac: str) -> bytes:
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(cleaned) != 12:
        raise ValueError(f"invalid MAC: {mac!r}")
    return bytes.fromhex(cleaned)


def magic_packet(mac: bytes) -> bytes:
    return b"\xff" * 6 + mac * 16


def load_hosts(path: Path) -> dict[str, tuple[str, str | None]]:
    hosts: dict[str, tuple[str, str | None]] = {}
    if not path.exists():
        return hosts
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("["):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name, mac = parts[0], parts[1]
        bcast = parts[2] if len(parts) > 2 else None
        hosts[name.lower()] = (mac, bcast)
    return hosts


def send_wol(mac: str, broadcast: str, port: int, repeat: int) -> None:
    payload = magic_packet(normalize_mac(mac))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for _ in range(repeat):
            sock.sendto(payload, (broadcast, port))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Wake-on-LAN magic packets")
    parser.add_argument("target", nargs="?", help="host alias from config or MAC aa:bb:cc:dd:ee:ff")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("-b", "--broadcast", default=DEFAULT_BROADCAST)
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-n", "--repeat", type=int, default=3)
    parser.add_argument("-l", "--list", action="store_true", help="list configured hosts")
    args = parser.parse_args()

    hosts = load_hosts(args.config)
    if args.list:
        if not hosts:
            print(f"No hosts in {args.config}", file=sys.stderr)
            return 1
        for name, (mac, bcast) in sorted(hosts.items()):
            extra = f"  broadcast={bcast}" if bcast else ""
            print(f"{name}\t{mac}{extra}")
        return 0

    if not args.target:
        parser.error("target required (host alias or MAC)")

    target = args.target.lower()
    mac = args.target
    broadcast = args.broadcast
    if target in hosts:
        mac, bcast = hosts[target]
        if bcast:
            broadcast = bcast

    try:
        send_wol(mac, broadcast, args.port, args.repeat)
    except OSError as exc:
        print(f"send failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"sent WoL x{args.repeat} to {mac} via {broadcast}:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
