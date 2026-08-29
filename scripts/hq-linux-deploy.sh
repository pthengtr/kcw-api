#!/usr/bin/env bash
set -euo pipefail
REPO="${HQ_KCW_API_DIR:-$HOME/projects/kcw-api}"
PY="${REPO}/.venv/bin/python"
cd "$REPO"
git fetch origin
git reset --hard origin/master
if [[ -x "$PY" ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PY" -r requirements.txt
  else
    "$PY" -m pip install -r requirements.txt
  fi
fi
systemctl --user restart kcw-tiger-pay.service kcw-stock-check.service kcw-parts9-explorer.service kcw-ops.service kcw-pay-notes.service kcw-transfer.service
if systemctl --user is-active --quiet kcw-worker.service; then
  if [[ "${FORCE_WORKER_RESTART:-}" == "1" ]]; then
    systemctl --user restart kcw-worker.service
  else
    echo "kcw-worker left running (set FORCE_WORKER_RESTART=1 to bounce)"
  fi
else
  systemctl --user start kcw-worker.service
fi
systemctl --user --no-pager --full status kcw-tiger-pay.service kcw-stock-check.service kcw-parts9-explorer.service kcw-ops.service kcw-pay-notes.service kcw-transfer.service kcw-worker.service | tail -n 50
