#!/usr/bin/env python3
"""Load approved substitute seed rows into catalog.* (optional Phase 1 follow-up).

Never auto-loads unreviewed Phase 0 dumps. Pass an approved CSV with columns:
  proposed_group_id,bcode,descr,evidence,confidence,hq_qtymin,hq_qtyoh2,syp_qtyoh2,notes

Skips ORPHAN-L1 rows. Dry-run by default.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "csv_path",
        type=Path,
        help="Approved CSV (e.g. docs/substitutes/approved-seed.csv)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write to Supabase catalog (default is dry-run)",
    )
    ap.add_argument(
        "--min-confidence",
        default="high",
        choices=("high", "med", "low"),
        help="Skip rows below this confidence (default: high)",
    )
    args = ap.parse_args()

    order = {"high": 0, "med": 1, "low": 2}
    min_rank = order[args.min_confidence]

    by_group: dict[str, list[dict]] = defaultdict(list)
    with args.csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gid = (row.get("proposed_group_id") or "").strip()
            bcode = (row.get("bcode") or "").strip()
            if not gid or not bcode or gid.startswith("ORPHAN"):
                continue
            conf = (row.get("confidence") or "low").strip().lower()
            if order.get(conf, 9) > min_rank:
                continue
            by_group[gid].append(row)

    print(f"groups={len(by_group)} members={sum(len(v) for v in by_group.values())}")
    for gid, rows in sorted(by_group.items()):
        bcodes = [r["bcode"] for r in rows]
        print(f"  {gid}: {', '.join(bcodes)}")

    if not args.apply:
        print("dry-run only; pass --apply to write")
        return 0

    from src.substitutes import db as sub_db

    client = sub_db.get_substitutes_supabase_client()
    created = 0
    for gid, rows in sorted(by_group.items()):
        note = (rows[0].get("notes") or rows[0].get("evidence") or "")[:500]
        members = [{"bcode": r["bcode"], "sort_rank": i} for i, r in enumerate(rows)]
        try:
            g = sub_db.create_group(
                client,
                name=gid,
                note=f"seed from {args.csv_path.name}: {note}",
                created_by="seed-script",
                members=members,
            )
            print(f"created {g['group_id']} from {gid}")
            created += 1
        except Exception as exc:
            print(f"SKIP {gid}: {exc}")
    print(f"created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
