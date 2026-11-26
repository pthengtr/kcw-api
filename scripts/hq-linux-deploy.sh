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

# Install unit from repo templates if missing, then enable it.
_ensure_unit() {
  local name="$1"
  local src="${REPO}/scripts/systemd/${name}.service"
  local dest="${HOME}/.config/systemd/user/${name}.service"
  if systemctl --user cat "${name}.service" &>/dev/null; then
    return 0
  fi
  if [[ ! -f "$src" ]]; then
    echo "WARNING: ${name} unit file missing in repo; not installed" >&2
    return 1
  fi
  mkdir -p "${HOME}/.config/systemd/user"
  cp "$src" "$dest"
  systemctl --user daemon-reload
  systemctl --user enable "${name}.service"
}

# All HQ local kcw-api app services (not timers / oneshots / analytics).
# Install-on-first-deploy, then always restart when the unit exists.
_hq_app_units=(
  kcw-tiger-pay
  kcw-stock-check
  kcw-parts9-explorer
  kcw-ops
  kcw-pay-notes
  kcw-receive-notes
  kcw-transfer
  kcw-hq-po
  kcw-hq-receive
  kcw-online-sale
  kcw-to-bill
)

_units=()
for name in "${_hq_app_units[@]}"; do
  if ! _ensure_unit "$name"; then
    continue
  fi
  if systemctl --user cat "${name}.service" &>/dev/null; then
    _units+=("$name")
  fi
done

for u in "${_units[@]}"; do
  systemctl --user restart "${u}.service"
  echo "restarted ${u}.service"
done

# Queue worker: always bounce unless SKIP_WORKER_RESTART=1.
if [[ "${SKIP_WORKER_RESTART:-}" == "1" ]]; then
  if systemctl --user is-active --quiet kcw-worker.service; then
    echo "kcw-worker left running (SKIP_WORKER_RESTART=1)"
  else
    systemctl --user start kcw-worker.service
  fi
elif systemctl --user is-active --quiet kcw-worker.service; then
  systemctl --user restart kcw-worker.service
else
  systemctl --user start kcw-worker.service
fi

# Support worker: do NOT bounce on every deploy — mid-ticket SIGTERM left
# tickets stuck in status=running (claim only picks pending). Opt in with
# RESTART_SUPPORT_WORKER=1 when support-worker code itself changed.
# Legacy: SKIP_SUPPORT_WORKER_RESTART=1 still means "leave running".
if systemctl --user cat kcw-support-worker.service &>/dev/null; then
  if [[ "${RESTART_SUPPORT_WORKER:-}" == "1" && "${SKIP_SUPPORT_WORKER_RESTART:-}" != "1" ]]; then
    systemctl --user restart kcw-support-worker.service
    echo "kcw-support-worker restarted (RESTART_SUPPORT_WORKER=1)"
  elif systemctl --user is-active --quiet kcw-support-worker.service; then
    echo "kcw-support-worker left running (set RESTART_SUPPORT_WORKER=1 to bounce)"
  else
    systemctl --user start kcw-support-worker.service
  fi
fi

_status_units=("${_units[@]/%/.service}" kcw-worker.service)
if systemctl --user cat kcw-support-worker.service &>/dev/null; then
  _status_units+=(kcw-support-worker.service)
fi
systemctl --user --no-pager --full status "${_status_units[@]}" | tail -n 80
