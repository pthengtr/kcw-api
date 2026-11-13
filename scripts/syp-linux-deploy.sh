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

_units=(kcw-stock-check kcw-parts9-explorer kcw-ops)
if systemctl --user cat kcw-transfer.service &>/dev/null; then
  _units+=(kcw-transfer)
fi
for u in "${_units[@]}"; do
  systemctl --user restart "${u}.service"
done
# Always bounce the worker on deploy so heartbeat/code fixes take effect.
# Long jobs are interrupted and reclaimed as failed on startup; set
# SKIP_WORKER_RESTART=1 only when you intentionally need to finish a run first.
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
