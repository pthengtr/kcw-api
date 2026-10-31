#!/usr/bin/env python3
"""Install PO insert blocks on KSS PARTS9 via SMB copy + WinRM sqlcmd -E."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import winrm
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
SQL_PATH = REPO / "scripts" / "sql" / "block_pomas_insert.sql"
load_dotenv(REPO / ".env")
load_dotenv(REPO.parent / "kcw-analytic" / ".env", override=False)

KSS_HOST = os.getenv("KSS_SMB_HOST", "192.168.1.99").split(",")[-1].strip()
KSS_SHARE = os.getenv("KSS_SMB_SHARE", "KAcc9")
KSS_USER = os.getenv("KSS_SMB_USER", "Administrator")
KSS_PASS = os.getenv("KSS_SMB_PASSWORD", "")
REMOTE_REL = r"TEMP\block_pomas_insert.sql"
LOCAL_SQL = r"D:\KAcc9\TEMP\block_pomas_insert.sql"


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


def _run(session: winrm.Session, ps: str) -> str:
    result = session.run_ps(ps)
    out = result.std_out.decode("utf-8", errors="replace")
    err = result.std_err.decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    if result.status_code != 0:
        raise SystemExit(f"KSS command failed ({result.status_code})")
    return out


def main() -> None:
    if not KSS_PASS:
        raise SystemExit("KSS_SMB_PASSWORD not set")
    text = SQL_PATH.read_text(encoding="utf-8")
    if "trg_POMAS_block_insert" not in text or "trg_PODET_block_insert" not in text:
        raise SystemExit(f"unexpected SQL file: {SQL_PATH}")

    _smb_put()
    session = winrm.Session(
        f"http://{KSS_HOST}:5985/wsman",
        auth=(KSS_USER, KSS_PASS),
        transport="ntlm",
    )
    _run(
        session,
        f"""
$ErrorActionPreference = 'Stop'
$path = '{LOCAL_SQL}'
if (-not (Test-Path $path)) {{ throw "missing $path" }}
sqlcmd -S localhost -d PARTS9 -E -b -I -i $path
if ($LASTEXITCODE -ne 0) {{ throw "sqlcmd exit $LASTEXITCODE" }}
sqlcmd -S localhost -d PARTS9 -E -W -s "|" -Q "SET NOCOUNT ON; SELECT name, is_disabled FROM sys.triggers WHERE name IN ('trg_POMAS_block_insert','trg_PODET_block_insert') ORDER BY name;"
""",
    )
    # A rejected insert must not leave a header. sqlcmd exits non-zero on THROW.
    probe = session.run_ps(
        r"""
$ErrorActionPreference = 'Continue'
sqlcmd -S localhost -d PARTS9 -E -b -f 65001 -Q "SET NOCOUNT ON; INSERT INTO dbo.POMAS (DOCNO) VALUES (N'BLOCK-TEST');"
$insertExit = $LASTEXITCODE
sqlcmd -S localhost -d PARTS9 -E -W -h-1 -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM dbo.POMAS WHERE LTRIM(RTRIM(DOCNO)) = N'BLOCK-TEST';"
if ($insertExit -eq 0) { throw "insert was allowed" }
"""
    )
    probe_out = probe.std_out.decode("utf-8", errors="replace")
    probe_err = probe.std_err.decode("utf-8", errors="replace")
    print(probe_out)
    if probe_err.strip():
        print(probe_err, file=sys.stderr)
    if probe.status_code != 0:
        raise SystemExit(f"KSS probe failed ({probe.status_code})")
    if "BLOCK-TEST" in probe_out and "0" not in probe_out.split():
        raise SystemExit("probe row still present")
    print("OK: PO insert blocked on KSS PARTS9")


if __name__ == "__main__":
    main()
