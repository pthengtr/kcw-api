#!/usr/bin/env python3
"""Fix transfer-service TF ship bills that wrote negative SIDET.QTY (2026-08-31 bug).

Also corrects ICMAS.QTYOH2 when receive increased stock but ship did not decrease.

Usage:
  cd ~/projects/kcw-api
  .venv/bin/python scripts/remediate_transfer_tf_qty_sign.py --dry-run
  .venv/bin/python scripts/remediate_transfer_tf_qty_sign.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

REPO = Path(__file__).resolve().parents[1]
load_dotenv(REPO / ".env")


def _fetch_negative_lines(*, branch: str, bill_date: date):
    from src.transfer.writers._engine import reader_engine_for_branch

    eng = reader_engine_for_branch(branch)
    with eng.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT s.BILLNO, d.BCODE, d.QTY, s.REMARKS
                FROM dbo.SIMAS s
                JOIN dbo.SIDET d
                  ON s.BILLNO = d.BILLNO
                 AND s.BILLDATE = d.BILLDATE
                 AND s.BILLTYPE = d.BILLTYPE
                WHERE CAST(s.BILLDATE AS date) = :bill_date
                  AND COALESCE(s.CANCELED, '') <> 'Y'
                  AND COALESCE(d.CANCELED, '') <> 'Y'
                  AND CONVERT(nvarchar(4000), s.REMARKS) LIKE 'TRF-%'
                  AND d.QTY < 0
                ORDER BY s.BILLNO, d.LINE
                """
            ),
            {"bill_date": bill_date},
        ).mappings().all()


def _apply_icmas_ship_correction(conn, *, bill_date: date) -> list[tuple[str, float, float]]:
    """Subtract ship qty that never left ICMAS (receive increased; ship did not decrease)."""
    rows = conn.execute(
        text(
            """
            SELECT LTRIM(RTRIM(d.BCODE)) AS bcode,
                   SUM(ABS(d.QTY)) AS qty_ship
            FROM dbo.SIDET d
            JOIN dbo.SIMAS s
              ON s.BILLNO = d.BILLNO
             AND s.BILLDATE = d.BILLDATE
             AND s.BILLTYPE = d.BILLTYPE
             AND s.JOURMODE = d.JOURMODE
            WHERE CAST(s.BILLDATE AS date) = :bill_date
              AND COALESCE(s.CANCELED, '') <> 'Y'
              AND COALESCE(d.CANCELED, '') <> 'Y'
              AND CONVERT(nvarchar(4000), s.REMARKS) LIKE 'TRF-%'
            GROUP BY LTRIM(RTRIM(d.BCODE))
            """
        ),
        {"bill_date": bill_date},
    ).mappings().all()
    out: list[tuple[str, float, float]] = []
    for row in rows:
        bcode = str(row["bcode"])
        qty_ship = float(row["qty_ship"] or 0)
        if qty_ship <= 0:
            continue
        live = conn.execute(
            text("SELECT QTYOH2 FROM dbo.ICMAS WHERE LTRIM(RTRIM(BCODE)) = :bcode"),
            {"bcode": bcode},
        ).scalar()
        old_icmas = float(live or 0)
        new_icmas = old_icmas - qty_ship
        conn.execute(
            text("UPDATE dbo.ICMAS SET QTYOH2 = :qty WHERE LTRIM(RTRIM(BCODE)) = :bcode"),
            {"qty": new_icmas, "bcode": bcode},
        )
        out.append((bcode, old_icmas, new_icmas))
    return out


def _apply_writer_fixes(*, branch: str, bill_date: date) -> None:
    from src.transfer.writers._engine import writer_engine_for_branch

    eng = writer_engine_for_branch(branch)
    with eng.begin() as conn:
        updated = conn.execute(
            text(
                """
                UPDATE d
                SET d.QTY = ABS(d.QTY)
                FROM dbo.SIDET d
                JOIN dbo.SIMAS s
                  ON s.BILLNO = d.BILLNO
                 AND s.BILLDATE = d.BILLDATE
                 AND s.BILLTYPE = d.BILLTYPE
                 AND s.JOURMODE = d.JOURMODE
                WHERE CAST(s.BILLDATE AS date) = :bill_date
                  AND COALESCE(s.CANCELED, '') <> 'Y'
                  AND COALESCE(d.CANCELED, '') <> 'Y'
                  AND CONVERT(nvarchar(4000), s.REMARKS) LIKE 'TRF-%'
                  AND d.QTY < 0
                """
            ),
            {"bill_date": bill_date},
        ).rowcount
        print(f"{branch}: flipped {updated} negative SIDET line(s)")
        for bcode, old_q, new_q in _apply_icmas_ship_correction(conn, bill_date=bill_date):
            print(f"{branch}: ICMAS {bcode} {old_q} -> {new_q}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bill-date", default="2026-08-31")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--hq-only", action="store_true")
    parser.add_argument("--syp-only", action="store_true")
    args = parser.parse_args()
    bill_date = datetime.strptime(args.bill_date, "%Y-%m-%d").date()

    branches = []
    if not args.syp_only:
        branches.append("HQ")
    if not args.hq_only:
        branches.append("SYP")

    for branch in branches:
        label = "KSS" if branch == "HQ" else "kss-pc"
        rows = _fetch_negative_lines(branch=branch, bill_date=bill_date)
        print(f"\n{label}: {len(rows)} negative TRF SIDET line(s)")
        for row in rows:
            print(f"  {row['BILLNO']} {row['BCODE']} QTY={row['QTY']}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to fix SIDET + ICMAS.")
        return

    for branch in branches:
        print(f"\nApplying {branch}...")
        _apply_writer_fixes(branch=branch, bill_date=bill_date)


if __name__ == "__main__":
    main()
