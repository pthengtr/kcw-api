#!/usr/bin/env bash
# Add LAN allow rules for kcw-online-sale (:8796) without resetting the whole firewall.
# Requires root. Prefer re-running hq-linux-firewall.sh when doing a full harden.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -E "$0" "$@"
fi

LAN_IF="${HQ_LAN_IF:-enp129s0}"
PORT=8796

ufw allow from 192.168.1.0/24 to any port "$PORT" proto tcp comment "KCW :$PORT LAN" || true
ufw allow in on "$LAN_IF" to any port "$PORT" proto tcp comment "KCW :$PORT LAN iface" || true
ufw status | grep -E "$PORT|Status" || true
echo "Port $PORT rules requested. Tailscale interface already allows inbound when enabled."
