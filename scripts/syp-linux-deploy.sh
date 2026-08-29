#!/usr/bin/env bash
# SYP Linux auto-deploy (GitHub Actions: syp-linux-deploy.yml, runner label linux+syp).
set -euo pipefail
REPO="${SYP_KCW_API_DIR:-$HOME/projects/kcw-api}"
PY="${REPO}/.venv/bin/python"
cd "$REPO"
git fetch origin
git reset --hard origin/master
DOCS="${SYP_KCW_DOCS_DIR:-$HOME/projects/kcw-docs}"
if [[ -d "$DOCS/.git" ]]; then
  cd "$DOCS"
  git fetch origin
  git reset --hard origin/main
  echo "kcw-docs at $(git rev-parse --short HEAD)"
  cd "$REPO"
fi
if [[ -x "$PY" ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PY" -r requirements.txt
  else
    "$PY" -m pip install -r requirements.txt
  fi
fi
_units=(kcw-stock-check kcw-parts9-explorer kcw-ops)
if systemctl --user cat kcw-transfer.service &>/dev/null; then
  _units+=(kcw-transfer)
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
