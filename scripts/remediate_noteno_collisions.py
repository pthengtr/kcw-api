#!/usr/bin/env python3
"""Remediate open pay notes where paid + open PIMAS share one vendor NOTENO."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.pay_notes.config import get_pay_notes_settings
from src.pay_notes.noteno_remediate import (
    list_open_mixed_noteno_collisions,
    remediate_open_mixed_noteno,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write KSS/Supabase changes")
    parser.add_argument("--acctno", default="", help="Limit to one vendor ACCTNO")
    parser.add_argument("--noteno", default="", help="Limit to one bare NOTENO")
    args = parser.parse_args()

    settings = get_pay_notes_settings()
    rows = list_open_mixed_noteno_collisions(settings.site)
    if args.acctno:
        rows = [r for r in rows if r.get("acctno", "").strip() == args.acctno.strip()]
    if args.noteno:
        rows = [r for r in rows if r.get("noteno", "").strip() == args.noteno.strip()]

    if not rows:
        print("No open mixed NOTENO collisions found.")
        return 0

    print(f"Found {len(rows)} collision(s){' — DRY RUN' if not args.apply else ''}:")
    for row in rows:
        print(
            f"  {row['acctno']} / {row['noteno']}: "
            f"paid={row['paid_cnt']} open={row['open_cnt']}"
        )

    for row in rows:
        result = remediate_open_mixed_noteno(
            site=settings.site,
            acctno=row["acctno"],
            bare_noteno=row["noteno"],
            dry_run=not args.apply,
        )
        if result:
            print(f"  -> {result}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
