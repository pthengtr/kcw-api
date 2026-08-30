#!/usr/bin/env bash
# Harden inbound on HQ Ubuntu: SSH, Tailscale, NoMachine, KCW LAN services only.
# Idempotent — safe to re-run after reboot or deploy.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -E "$0" "$@"
fi

LAN_IF="${HQ_LAN_IF:-enp129s0}"

ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing

ufw allow OpenSSH comment 'SSH'
ufw allow 41641/udp comment 'Tailscale wireguard'
ufw allow in on tailscale0 comment 'Tailscale interface'

ufw allow from 192.168.1.0/24 to any port 22 proto tcp comment 'SSH LAN'
ufw allow from 192.168.1.0/24 to any port 3389 proto tcp comment 'GNOME RDP LAN'
ufw allow from 192.168.1.0/24 to any port 4000 proto tcp comment 'NoMachine TCP LAN'
ufw allow from 192.168.1.0/24 to any port 4000 proto udp comment 'NoMachine UDP LAN'

for port in 8000 8787 8788 8790 8791 8792; do
  ufw allow from 192.168.1.0/24 to any port "$port" proto tcp comment "KCW :$port LAN"
  ufw allow in on "$LAN_IF" to any port "$port" proto tcp comment "KCW :$port LAN iface"
done

ufw allow 4000/udp comment 'NoMachine'
ufw allow 5353/udp comment 'mDNS'

ufw --force enable

echo
ufw status verbose
