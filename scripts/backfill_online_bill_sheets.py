#!/usr/bin/env python3
"""Snapshot TAD/CNTAD print HTML into online_sale.bill_sheets for the VAT register."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from src.online_sale.service import print_cntad_html, print_tad_html
from src.parts9_explorer.db import get_site_engine


def _list_billnos(*, since: str, kinds: tuple[str, ...], limit: int) -> list[tuple[str, str]]:
    engine = get_site_engine("hq")
    prefixes = []
    if "tad" in kinds:
        prefixes.extend(["TAD%", "3TAD%"])
    if "cntad" in kinds:
        prefixes.extend(["CNTAD%", "3CNTAD%"])
    like_sql = " OR ".join("LTRIM(RTRIM(BILLNO)) LIKE :p%d" % i for i in range(len(prefixes)))
    params = {f"p{i}": p for i, p in enumerate(prefixes)}
    params["since"] = since
    params["limit"] = limit
    sql = text(
        f"""
        SELECT TOP (:limit)
          LTRIM(RTRIM(BILLNO)) AS billno,
          CASE
            WHEN LTRIM(RTRIM(BILLNO)) LIKE '3CNTAD%' OR LTRIM(RTRIM(BILLNO)) LIKE 'CNTAD%'
              THEN 'cntad'
            ELSE 'tad'
          END AS kind
        FROM dbo.SIMAS WITH (NOLOCK)
        WHERE COALESCE(CANCELED, 'N') <> 'Y'
          AND ({like_sql})
          AND CONVERT(date, BILLDATE) >= CONVERT(date, :since)
        ORDER BY BILLDATE DESC, BILLNO DESC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        billno = str(row.get("billno") or "").strip().upper()
        kind = str(row.get("kind") or "").strip().lower()
        if not billno or billno in seen:
            continue
        seen.add(billno)
        out.append((billno, kind))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default="2026-11-01", help="Include bills on/after this date")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--kinds", default="tad,cntad")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    kinds = tuple(k.strip().lower() for k in args.kinds.split(",") if k.strip())
    rows = _list_billnos(since=args.since, kinds=kinds, limit=args.limit)
    print(f"found {len(rows)} bills since {args.since}")
    ok = 0
    failed = 0
    for billno, kind in rows:
        if args.dry_run:
            print(f"dry-run {kind} {billno}")
            ok += 1
            continue
        try:
            if kind == "cntad":
                print_cntad_html(billno)
            else:
                print_tad_html(billno)
            ok += 1
            if ok % 25 == 0:
                print(f"... {ok}/{len(rows)}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {billno}: {exc}")
    print(f"done ok={ok} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
