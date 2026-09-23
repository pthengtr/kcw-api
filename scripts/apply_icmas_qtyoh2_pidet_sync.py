#!/usr/bin/env python3
"""Install trg_PIDET_sync_icmas_qtyoh2 on KSS PARTS9 via SMB copy + WinRM sqlcmd -E."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import winrm
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
SQL_PATH = REPO / "scripts" / "sql" / "icmas_qtyoh2_pidet_sync.sql"
load_dotenv(REPO / ".env")
load_dotenv(REPO.parent / "kcw-analytic" / ".env", override=False)

KSS_HOST = os.getenv("KSS_SMB_HOST", "192.168.1.99").split(",")[-1].strip()
KSS_SHARE = os.getenv("KSS_SMB_SHARE", "KAcc9")
KSS_USER = os.getenv("KSS_SMB_USER", "Administrator")
KSS_PASS = os.getenv("KSS_SMB_PASSWORD", "")
REMOTE_REL = r"TEMP\icmas_qtyoh2_pidet_sync.sql"
LOCAL_SQL = r"D:\KAcc9\TEMP\icmas_qtyoh2_pidet_sync.sql"


def _smb_put() -> None:
    cmd = [
        "smbclient",
        f"//{KSS_HOST}/{KSS_SHARE}",
        "-U",
        f"{KSS_USER}%{KSS_PASS}",
        "-c",
        f"put {SQL_PATH} {REMOTE_REL}",
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    if not KSS_PASS:
        raise SystemExit("KSS_SMB_PASSWORD not set")
    if "trg_PIDET_sync_icmas_qtyoh2" not in SQL_PATH.read_text(encoding="utf-8"):
        raise SystemExit(f"unexpected SQL file: {SQL_PATH}")

    _smb_put()
    ps = f"""
$ErrorActionPreference = 'Stop'
$path = '{LOCAL_SQL}'
if (-not (Test-Path $path)) {{ throw "missing $path" }}
sqlcmd -S localhost -d PARTS9 -E -b -I -i $path
if ($LASTEXITCODE -ne 0) {{ throw "sqlcmd exit $LASTEXITCODE" }}
sqlcmd -S localhost -d PARTS9 -E -W -Q "SELECT name, is_disabled, create_date, modify_date FROM sys.triggers WHERE name = 'trg_PIDET_sync_icmas_qtyoh2';"
"""
    session = winrm.Session(
        f"http://{KSS_HOST}:5985/wsman",
        auth=(KSS_USER, KSS_PASS),
        transport="ntlm",
    )
    result = session.run_ps(ps)
    out = result.std_out.decode("utf-8", errors="replace")
    err = result.std_err.decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    if result.status_code != 0:
        raise SystemExit(f"KSS install failed ({result.status_code})")
    print("OK: trg_PIDET_sync_icmas_qtyoh2 installed on KSS PARTS9")


if __name__ == "__main__":
    main()
