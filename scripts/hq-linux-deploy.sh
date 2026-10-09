#!/usr/bin/env bash
set -euo pipefail
REPO="${HQ_KCW_API_DIR:-$HOME/projects/kcw-api}"
PY="${REPO}/.venv/bin/python"
cd "$REPO"

if [[ "${1:-}" != "--already-pulled" ]]; then
  git fetch origin
  git reset --hard origin/master
fi

DOCS="${HQ_KCW_DOCS_DIR:-$HOME/projects/kcw-docs}"
if [[ -d "$DOCS/.git" ]]; then
  cd "$DOCS"
  git fetch origin
  git reset --hard origin/main
  echo "kcw-docs at $(git rev-parse --short HEAD)"
  cd "$REPO"
fi

_install_reqs() {
  if ! [[ -x "$PY" ]]; then
    echo "WARNING: missing venv python at $PY; skipping requirements" >&2
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PY" -r requirements.txt
    return
  fi
  if ! "$PY" -m pip --version >/dev/null 2>&1; then
    echo "venv pip missing — bootstrapping with ensurepip"
    "$PY" -m ensurepip --upgrade
    "$PY" -m pip install -U pip
  fi
  "$PY" -m pip install -r requirements.txt
}

if ! _install_reqs; then
  echo "WARNING: requirements install failed; continuing with service restart" >&2
fi

_units=(kcw-tiger-pay kcw-stock-check kcw-parts9-explorer kcw-ops kcw-pay-notes)
if systemctl --user cat kcw-transfer.service &>/dev/null; then
  _units+=(kcw-transfer)
fi

# สั่งซื้อ is HQ-only. Install the unit once if it was never enabled, then
# restart it with the rest so a git pull actually reaches port 8793.
_install_hq_po_unit() {
  local src="${REPO}/scripts/systemd/kcw-hq-po.service"
  local dest="${HOME}/.config/systemd/user/kcw-hq-po.service"
  if systemctl --user cat kcw-hq-po.service &>/dev/null; then
    return 0
  fi
  if [[ ! -f "$src" ]]; then
    echo "WARNING: kcw-hq-po unit file missing; service not restarted" >&2
    return 0
  fi
  mkdir -p "${HOME}/.config/systemd/user"
  cp "$src" "$dest"
  systemctl --user daemon-reload
  systemctl --user enable kcw-hq-po.service
}
if ! _install_hq_po_unit; then
  echo "WARNING: could not install kcw-hq-po.service" >&2
fi
if systemctl --user cat kcw-hq-po.service &>/dev/null; then
  _units+=(kcw-hq-po)
fi
for u in "${_units[@]}"; do
  systemctl --user restart "${u}.service"
done
if systemctl --user is-active --quiet kcw-worker.service; then
  if [[ "${FORCE_WORKER_RESTART:-}" == "1" ]]; then
    systemctl --user restart kcw-worker.service
  else
    echo "kcw-worker left running (set FORCE_WORKER_RESTART=1 to bounce)"
  fi
else
  systemctl --user start kcw-worker.service
fi
systemctl --user --no-pager --full status "${_units[@]/%/.service}" kcw-worker.service | tail -n 50
