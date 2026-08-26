#!/usr/bin/env bash
# Wake kss-pc (KSS-PC) on shop LAN. Run from syp-ubuntu-server on enp3s0.
set -euo pipefail

MAC="${KSS_PC_MAC:-6c:0b:5e:47:06:d1}"
LAN_IP="${KSS_PC_LAN_IP:-192.168.1.189}"
BROADCAST="${KSS_PC_BROADCAST:-192.168.1.255}"
IFACE="${KSS_PC_IFACE:-enp3s0}"
WAIT_SEC="${KSS_PC_WAKE_WAIT:-45}"

if ! ping -c1 -W1 "$LAN_IP" >/dev/null 2>&1; then
  echo "kss-pc ($LAN_IP) already offline — good for WoL test"
else
  echo "WARNING: kss-pc ($LAN_IP) responds to ping (awake)."
  echo "Put it to Sleep (not Shutdown) on Windows, then re-run this script."
  echo "Continuing anyway (harmless if already awake)..."
fi

command -v wakeonlan >/dev/null || { echo "install: sudo apt install wakeonlan"; exit 1; }

echo "Sending WoL to $MAC via $BROADCAST on $IFACE ..."
wakeonlan -i "$BROADCAST" -p 9 "$MAC"
if command -v etherwake >/dev/null; then
  sudo etherwake -i "$IFACE" "$MAC" || true
fi

echo "Waiting ${WAIT_SEC}s for kss-pc to wake ..."
for i in $(seq 1 "$WAIT_SEC"); do
  if ping -c1 -W1 "$LAN_IP" >/dev/null 2>&1; then
    echo "SUCCESS: kss-pc responded after ${i}s"
    tailscale status 2>/dev/null | grep -i kss-pc || true
    exit 0
  fi
  sleep 1
done

echo "FAIL: no ping from $LAN_IP after ${WAIT_SEC}s"
echo "Check Windows: NIC WoL enabled, sleep not shutdown, same LAN."
exit 1
