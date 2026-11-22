#!/usr/bin/env bash
# SYP Linux auto-deploy (GitHub Actions: syp-linux-deploy.yml, runner label linux+syp).
set -euo pipefail
REPO="${SYP_KCW_API_DIR:-$HOME/projects/kcw-api}"
PY="${REPO}/.venv/bin/python"
cd "$REPO"

if [[ "${1:-}" != "--already-pulled" ]]; then
  git fetch origin
  git reset --hard origin/master
fi

DOCS="${SYP_KCW_DOCS_DIR:-$HOME/projects/kcw-docs}"
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

# Code pull already succeeded; don't block service bounce on a broken pip.
if ! _install_reqs; then
  echo "WARNING: requirements install failed; continuing with service restart" >&2
fi

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

# SYP-hosted app services only (HQ-only companion/pay-notes/receive-notes/online-sale/hq-*).
_syp_app_units=(
  kcw-stock-check
  kcw-parts9-explorer
  kcw-ops
  kcw-transfer
)

_units=()
for name in "${_syp_app_units[@]}"; do
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

systemctl --user --no-pager --full status "${_units[@]/%/.service}" kcw-worker.service | tail -n 50
