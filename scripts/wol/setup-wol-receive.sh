#!/usr/bin/env bash
# Enable Wake-on-LAN on the wired NIC (run once with sudo on hq-ubuntu-server).
set -euo pipefail

IFACE="${WOL_IFACE:-enp129s0}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run: sudo $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
if ! command -v ethtool >/dev/null; then
  apt-get update -qq
  apt-get install -y ethtool
fi

ethtool -s "$IFACE" wol g
echo "Wake-on-LAN enabled on $IFACE:"
ethtool "$IFACE" | grep -i 'Wake-on'

CONN="$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: -v d="$IFACE" '$2==d {print $1; exit}')"
if [[ -n "${CONN}" ]]; then
  nmcli connection modify "$CONN" 802-3-ethernet.wake-on-lan magic
  echo "NetworkManager: $CONN -> wake-on-lan magic"
fi

install -m 644 "$ROOT/wol-enp129s0.service" /etc/systemd/system/wol-enp129s0.service
systemctl daemon-reload
systemctl enable --now wol-enp129s0.service
echo "Installed wol-enp129s0.service (persists wol g across reboot)"
