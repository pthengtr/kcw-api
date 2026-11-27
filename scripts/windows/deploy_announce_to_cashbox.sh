#!/usr/bin/env bash
# Deploy cloud QR announce worker to the Tiger cashbox (Windows SSH).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${CASHBOX_SSH_KEY:-$HOME/.ssh/cashbox}"
HOST="${CASHBOX_SSH_HOST:-Administrator@192.168.1.20}"
REMOTE_DIR='C:/KCW/announce'
SSH=(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "$HOST")
SCP=(scp -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

echo "== ensure remote dirs =="
"${SSH[@]}" cmd /c "if not exist C:\\KCW mkdir C:\\KCW & if not exist C:\\KCW\\announce mkdir C:\\KCW\\announce & if not exist C:\\KCW\\announce\\src mkdir C:\\KCW\\announce\\src & if not exist C:\\KCW\\announce\\src\\db mkdir C:\\KCW\\announce\\src\\db & if not exist C:\\KCW\\announce\\src\\tiger_pay mkdir C:\\KCW\\announce\\src\\tiger_pay"

echo "== copy python package =="
"${SCP[@]}" \
  "$ROOT/src/db/__init__.py" \
  "$ROOT/src/db/config.py" \
  "$ROOT/src/db/engine.py" \
  "$HOST:$REMOTE_DIR/src/db/"
"${SCP[@]}" \
  "$ROOT/src/tiger_pay/__init__.py" \
  "$ROOT/src/tiger_pay/cloud_qr_repos.py" \
  "$ROOT/src/tiger_pay/announce_tts.py" \
  "$ROOT/src/tiger_pay/announce_worker.py" \
  "$HOST:$REMOTE_DIR/src/tiger_pay/"
"${SCP[@]}" \
  "$ROOT/requirements-announce.txt" \
  "$ROOT/scripts/windows/Install-AnnounceWorker.ps1" \
  "$HOST:$REMOTE_DIR/"

# Empty package markers / run helper
"${SSH[@]}" cmd /c "echo. > C:\\KCW\\announce\\src\\__init__.py"

echo "== write .env (SUPABASE_DB_* only) =="
python3 - <<'PY' > /tmp/kcw_announce.env
from pathlib import Path
src = Path("/home/hqadmin/projects/kcw-api/.env")
keys = {
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_PORT",
    "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD",
}
out = [
    "ANNOUNCE_WORKER_ID=tiger-cashbox",
    "ANNOUNCE_POLL_INTERVAL_SECONDS=1",
    "ANNOUNCE_LOOKBACK_HOURS=24",
    "ANNOUNCE_DRY_RUN=0",
    "ANNOUNCE_EDGE_VOICE=th-TH-NiwatNeural",
]
for line in src.read_text(encoding="utf-8").splitlines():
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    if k in keys:
        out.append(f"{k}={v}")
missing = keys - {l.split("=", 1)[0] for l in out}
if missing:
    raise SystemExit(f"missing env keys: {sorted(missing)}")
print("\n".join(out) + "\n")
PY
"${SCP[@]}" /tmp/kcw_announce.env "$HOST:$REMOTE_DIR/.env"
rm -f /tmp/kcw_announce.env

echo "== done copy; install python/venv on box next =="
