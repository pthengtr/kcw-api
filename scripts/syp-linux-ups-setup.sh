#!/usr/bin/env bash
# Configure NUT for Syndome Claire on SYP Ubuntu (CH340 /dev/ttyUSB0).
# Idempotent — safe to re-run.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -E "$0" "$@"
fi

UPS_NAME="${NUT_UPS_NAME:-claire}"
UPS_PORT="${NUT_UPS_PORT:-/dev/ttyUSB0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USERS_FILE=/etc/nut/upsd.users
MONITOR_PASS=""

apt-get install -y nut nut-client nut-server

install -m 0755 "${SCRIPT_DIR}/nut-fsd-shutdown.sh" /usr/local/sbin/nut-fsd-shutdown.sh

if [[ ! -f /etc/default/nut-fsd-shutdown ]]; then
  cat >/etc/default/nut-fsd-shutdown <<'EOF'
# Seconds until RTC wake after soft-off (power-race backup).
RTC_WAKE_SECS=1800
EOF
fi

cat >/etc/nut/nut.conf <<'EOF'
MODE=standalone
EOF

cat >/etc/nut/ups.conf <<EOF
maxretry = 3
pollinterval = 2

[${UPS_NAME}]
	driver = blazer_ser
	port = ${UPS_PORT}
	desc = "Syndome Claire"
	allow_killpower
	sdcommands = shutdown.return
EOF

if [[ -f "$USERS_FILE" ]] && grep -q '^\[upsmon\]' "$USERS_FILE"; then
  MONITOR_PASS="$(awk '/^\[upsmon\]/{f=1} f && /^[[:space:]]*password/{print $3; exit}' "$USERS_FILE")"
fi
if [[ -z "$MONITOR_PASS" ]]; then
  MONITOR_PASS="$(openssl rand -hex 12)"
  cat >"$USERS_FILE" <<EOF
[upsmon]
	password = ${MONITOR_PASS}
	upsmon master
	actions = SET
	instcmds = ALL
EOF
  chmod 640 "$USERS_FILE"
  chown root:nut "$USERS_FILE"
  echo "Generated upsmon password in ${USERS_FILE} (not printed)."
fi

cat >/etc/nut/upsmon.conf <<EOF
RUN_AS_USER nut
MONITOR ${UPS_NAME}@localhost 1 upsmon ${MONITOR_PASS} master
MINSUPPLIES 1
SHUTDOWNCMD "/usr/local/sbin/nut-fsd-shutdown.sh"
POWERDOWNFLAG /etc/killpower
FINALDELAY 5
EOF

usermod -aG dialout nut || true

systemctl reset-failed nut-server nut-monitor 2>/dev/null || true
systemctl enable nut-driver@"${UPS_NAME}" nut-server nut-monitor
systemctl restart nut-driver@"${UPS_NAME}" nut-server nut-monitor

sleep 3
echo
echo "=== upsc ${UPS_NAME}@localhost ==="
upsc "${UPS_NAME}@localhost" ups.status battery.charge ups.load device.mfr device.model 2>&1 || {
  echo "NUT driver not responding — check ${UPS_PORT} and USB cable." >&2
  exit 1
}
