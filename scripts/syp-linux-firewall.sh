#!/usr/bin/env bash
# Harden inbound on SYP Ubuntu: SSH, Tailscale, NoMachine, KCW LAN services only.
# Idempotent — safe to re-run after reboot or deploy.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -E "$0" "$@"
fi

LAN_IF="${SYP_LAN_IF:-enp3s0}"

ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing

ufw allow OpenSSH comment 'SSH'
ufw allow 41641/udp comment 'Tailscale wireguard'
ufw allow in on tailscale0 comment 'Tailscale interface'

ufw allow 4000/tcp comment 'NoMachine'
ufw allow 4000/udp comment 'NoMachine'

for port in 8787 8788 8790 8792; do
  ufw allow in on "$LAN_IF" to any port "$port" proto tcp comment "KCW :$port LAN"
done

ufw --force enable

echo
ufw status verbose
