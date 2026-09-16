#!/usr/bin/env bash
# Standalone Samba share [files] -> /home/hqadmin/kcw-files
# Root: apt smbd. Otherwise: Docker --network host (port 445; same smb.conf).
# Idempotent. Does not reset UFW.
set -euo pipefail

SHARE_USER="${SHARE_USER:-hqadmin}"
SHARE_PATH="${SHARE_PATH:-/home/${SHARE_USER}/kcw-files}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_CONF="${SCRIPT_DIR}/samba/smb.conf"
PASS_FILE="/home/${SHARE_USER}/.config/kcw/samba-files.pass"
IMAGE="${SAMBA_IMAGE:-kcw-samba:local}"
NAME="${SAMBA_CONTAINER:-kcw-samba}"
FOREGROUND=0

if [[ "${1:-}" == "--foreground" ]]; then
  FOREGROUND=1
fi

if [[ ! -f "$REPO_CONF" ]]; then
  echo "missing $REPO_CONF" >&2
  exit 1
fi

ensure_pass_and_dir() {
  install -d -m 700 "$(dirname "$PASS_FILE")"
  if [[ ! -s "$PASS_FILE" ]]; then
    openssl rand -base64 18 | tr -d '\n\r' >"$PASS_FILE"
    echo >>"$PASS_FILE"
    chmod 600 "$PASS_FILE"
    echo "wrote new Samba password to $PASS_FILE"
  fi
  chmod 600 "$PASS_FILE"
  install -d -m 770 "$SHARE_PATH"
}

apply_native() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y samba samba-vfs-modules
  SHARE_UID="$(id -u "$SHARE_USER")"
  env XDG_RUNTIME_DIR="/run/user/${SHARE_UID}" \
    systemctl --machine="${SHARE_USER}@" --user disable --now kcw-samba.service 2>/dev/null || true
  docker rm -f "$NAME" 2>/dev/null || true

  if [[ -f /etc/samba/smb.conf && ! -f /etc/samba/smb.conf.ubuntu-sample ]]; then
    cp -a /etc/samba/smb.conf /etc/samba/smb.conf.ubuntu-sample
  fi
  install -m 644 "$REPO_CONF" /etc/samba/smb.conf
  testparm -s >/dev/null

  PASS="$(tr -d '\n\r' <"$PASS_FILE")"
  printf '%s\n%s\n' "$PASS" "$PASS" | smbpasswd -a "$SHARE_USER" -s
  smbpasswd -e "$SHARE_USER"

  systemctl disable --now nmbd.service 2>/dev/null || true
  systemctl mask nmbd.service 2>/dev/null || true
  systemctl enable --now smbd.service

  if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -qi '^Status: active'; then
    ufw allow from 192.168.1.0/24 to any port 445 proto tcp comment 'Samba SMB LAN' || true
    echo "UFW active: ensured 445/tcp from 192.168.1.0/24"
  fi
}

run_docker_foreground() {
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    docker build -t "$IMAGE" "${SCRIPT_DIR}/samba"
  fi
  docker rm -f "$NAME" 2>/dev/null || true
  exec docker run --rm --name "$NAME" --network host \
    -v "${SHARE_PATH}:/home/hqadmin/kcw-files" \
    -v "${PASS_FILE}:/run/smb.pass:ro" \
    -v "${REPO_CONF}:/etc/samba/smb.conf:ro" \
    "$IMAGE"
}

apply_docker() {
  docker build -t "$IMAGE" "${SCRIPT_DIR}/samba"
  UNIT_DIR="/home/${SHARE_USER}/.config/systemd/user"
  install -d "$UNIT_DIR"
  install -m 644 "${SCRIPT_DIR}/samba/kcw-samba.service" "${UNIT_DIR}/kcw-samba.service"
  systemctl --user daemon-reload
  systemctl --user enable kcw-samba.service
  systemctl --user restart kcw-samba.service
}

ensure_pass_and_dir

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  apply_native
elif [[ "$FOREGROUND" -eq 1 ]]; then
  run_docker_foreground
else
  apply_docker
fi

for _ in 1 2 3 4 5 6 7 8 9 10; do
  ss -lnt | grep -qE ':445' && break
  sleep 1
done
ss -lnt | grep -E ':445' || { echo "nothing listening on 445" >&2; exit 1; }
echo "Samba [files] data dir: $SHARE_PATH"
