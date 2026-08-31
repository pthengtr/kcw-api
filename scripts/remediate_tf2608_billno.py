#!/usr/bin/env python3
"""Rename transfer-created TF2608-* bill to Buddhist TF6908-* and sync Supabase."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import winrm
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
load_dotenv(REPO / ".env")

OLD_BILL = "TF2608-00001"
NEW_BILL = "TF6908-0098"
SHIPMENT_ID = "bcda7816-7d3f-4938-9cc4-809ea89b2a40"
KSS_HOST = os.getenv("KSS_SMB_HOST", "192.168.1.99").split(",")[-1].strip()
KSS_USER = os.getenv("KSS_SMB_USER", "Administrator")
KSS_PASS = os.getenv("KSS_SMB_PASSWORD", "")


def _run_kss_sql() -> None:
    if not KSS_PASS:
        raise SystemExit("KSS_SMB_PASSWORD not set")
    ps = f"""
$sql = @"
SET XACT_ABORT ON;
BEGIN TRAN;
UPDATE dbo.SIDET SET BILLNO = '{NEW_BILL}' WHERE BILLNO = '{OLD_BILL}';
UPDATE dbo.SIMAS SET BILLNO = '{NEW_BILL}' WHERE BILLNO = '{OLD_BILL}';
COMMIT TRAN;
SELECT BILLNO, REMARKS FROM dbo.SIMAS WHERE BILLNO = '{NEW_BILL}';
SELECT BILLNO, BCODE, QTY FROM dbo.SIDET WHERE BILLNO = '{NEW_BILL}';
"@
$sql | sqlcmd -S localhost -d PARTS9 -E -W
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
        raise SystemExit(f"KSS sqlcmd failed ({result.status_code})")


def _update_supabase() -> None:
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)
    rows = (
        client.schema("transfer")
        .from_("shipments")
        .update({"ship_billno": NEW_BILL, "tf_billno": NEW_BILL})
        .eq("shipment_id", SHIPMENT_ID)
        .execute()
    )
    print("supabase shipments:", rows.data)


def _show_next_bill() -> None:
    sys.path.insert(0, str(REPO))
    from src.transfer.writers._engine import next_simas_billno, writer_engine_for_branch

    eng = writer_engine_for_branch("HQ")
    with eng.connect() as conn:
        nxt = next_simas_billno(conn, from_branch="HQ", when=datetime.now())
    print("next HQ TF bill:", nxt)


def main() -> None:
    _run_kss_sql()
    _update_supabase()
    _show_next_bill()


if __name__ == "__main__":
    main()
