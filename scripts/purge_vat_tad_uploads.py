#!/usr/bin/env python3
"""Delete staff-uploaded TAD/CNTAD invoice files replaced by online-sale sheets.

Only removes uploads for bills on/after ONLINE_TAX_AUTO_ATTACH_FROM (2026-11-01).
Older TAD/CNTAD uploads stay — those rows still require a staff file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(ROOT / ".env")

BUCKET = "vat-documents"
AUTO_FROM = "2026-11-01"
DOC_TYPES = ["TAD", "CNTAD", "3TAD", "3CNTAD"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch", type=int, default=100)
    parser.add_argument("--since", default=AUTO_FROM)
    args = parser.parse_args()

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    sb = create_client(url, key)

    rows: list[dict] = []
    offset = 0
    while True:
        res = (
            sb.schema("ops")
            .from_("vat_line_files")
            .select(
                "id,line_key,kind,storage_path,"
                "vat_line_evidence!inner(doc_type,bill_no,bill_date)"
            )
            .eq("kind", "invoice")
            .in_("vat_line_evidence.doc_type", DOC_TYPES)
            .gte("vat_line_evidence.bill_date", args.since)
            .range(offset, offset + args.batch - 1)
            .execute()
        )
        chunk = res.data or []
        rows.extend(chunk)
        if len(chunk) < args.batch:
            break
        offset += args.batch

    print(f"found {len(rows)} uploaded TAD/CNTAD invoice files since {args.since}")
    if args.dry_run:
        for row in rows[:20]:
            ev = row.get("vat_line_evidence") or {}
            print(
                f"dry-run {ev.get('doc_type')} {ev.get('bill_no')} "
                f"{ev.get('bill_date')} {row.get('storage_path')}"
            )
        if len(rows) > 20:
            print(f"... and {len(rows) - 20} more")
        return 0

    removed = 0
    failed = 0
    for i in range(0, len(rows), args.batch):
        batch = rows[i : i + args.batch]
        paths = [str(r["storage_path"]) for r in batch if r.get("storage_path")]
        ids = [str(r["id"]) for r in batch if r.get("id")]
        if paths:
            try:
                sb.storage.from_(BUCKET).remove(paths)
            except Exception as exc:
                print("storage error", exc)
                failed += len(paths)
                continue
        if ids:
            sb.schema("ops").from_("vat_line_files").delete().in_("id", ids).execute()
        removed += len(batch)
        print(f"... removed {removed}/{len(rows)}")

    print(f"done removed={removed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
