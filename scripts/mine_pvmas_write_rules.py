#!/usr/bin/env python3
"""Read-only KSS mining for PVMAS/PIMAS/BPDET write rules (pay notes service).

Usage:
  cd projects/kcw-api && .venv/bin/python scripts/mine_pvmas_write_rules.py [--site hq]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.parts9_explorer.db import get_site_engine  # noqa: E402


def _rows(conn, sql: str, **params):
    return [dict(r) for r in conn.execute(text(sql), params).mappings().all()]


def mine(site: str) -> dict:
    eng = get_site_engine(site)
    out: dict = {"site": site.upper(), "tables": {}}
    with eng.connect() as conn:
        out["note_only_count"] = conn.execute(
            text(
                """
                SELECT COUNT(*) AS c FROM dbo.PVMAS
                WHERE NOTED = 'Y' AND ISNULL(VOUCED, 'N') = 'N'
                  AND ISNULL(CANCELED, 'N') <> 'Y'
                """
            )
        ).scalar()

        out["note_only_sample"] = _rows(
            conn,
            """
            SELECT TOP 5 NOTENO, NOTEDATE, ACCTNO, ACCTNAME, BILLCNT, BILLAMT,
                   JOURTYPE, JOURMODE, DEPTNO, BOOKNO,
                   DISCOUNT, NETAMT, PAYAMT, PAID, POSTED1, POSTED2, DONE, CANCELED
            FROM dbo.PVMAS
            WHERE NOTED = 'Y' AND ISNULL(VOUCED, 'N') = 'N'
            ORDER BY NOTEDATE DESC
            """,
        )

        out["billamt_check"] = _rows(
            conn,
            """
            SELECT TOP 5 p.NOTENO, p.ACCTNO, p.BILLAMT, p.BILLCNT,
                   (SELECT SUM(i.AFTERTAX) FROM dbo.PIMAS i
                    WHERE LTRIM(RTRIM(i.ACCTNO)) = LTRIM(RTRIM(p.ACCTNO))
                      AND LTRIM(RTRIM(i.NOTENO)) = LTRIM(RTRIM(p.NOTENO))) AS sum_aftertax
            FROM dbo.PVMAS p
            WHERE p.NOTED = 'Y' AND ISNULL(p.VOUCED, 'N') = 'N' AND p.BILLCNT > 1
            ORDER BY p.NOTEDATE DESC
            """,
        )

        out["jourmode_split"] = _rows(
            conn,
            """
            SELECT JOURMODE, COUNT(*) AS c FROM dbo.PVMAS
            WHERE NOTED = 'Y' AND ISNULL(VOUCED, 'N') = 'N'
            GROUP BY JOURMODE ORDER BY c DESC
            """,
        )

        out["voucher_sample"] = _rows(
            conn,
            """
            SELECT TOP 3 VOUCNO, VOUCDATE, NOTENO, ACCTNO, BILLAMT, DISCOUNT, NETAMT,
                   PAYAMT, CHKAMT, PAID, NOTED, VOUCED
            FROM dbo.PVMAS
            WHERE VOUCED = 'Y' AND ISNULL(CANCELED, 'N') <> 'Y'
            ORDER BY VOUCDATE DESC
            """,
        )

        out["voucno_max_kcpn"] = dict(
            conn.execute(
                text(
                    """
                    SELECT MAX(VOUCNO) AS mx FROM dbo.PVMAS
                    WHERE VOUCNO LIKE 'KCPN' + RIGHT(CONVERT(varchar(4), YEAR(GETDATE())), 2)
                        + RIGHT('0' + CONVERT(varchar(2), MONTH(GETDATE())), 2) + '-%'
                    """
                )
            ).mappings().first()
            or {}
        )

        out["bpdet_sample"] = _rows(
            conn,
            """
            SELECT TOP 5 VOUCNO, VOUCDATE, CHKNO, CHKDATE, CHKAMT, BANKNAME, ACCTNO, PAYTYPE, JOURTYPE
            FROM dbo.BPDET
            WHERE ISNULL(CANCELED, 'N') <> 'Y'
            ORDER BY VOUCDATE DESC
            """,
        )

        for table in ("PVMAS", "PIMAS", "BPDET"):
            out["tables"][table] = _rows(
                conn,
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :t
                ORDER BY ORDINAL_POSITION
                """,
                t=table,
            )

        out["triggers"] = _rows(
            conn,
            """
            SELECT t.name AS table_name, tr.name AS trigger_name
            FROM sys.triggers tr
            JOIN sys.tables t ON tr.parent_id = t.object_id
            WHERE t.name IN ('PVMAS', 'PIMAS', 'BPDET')
            """,
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine KSS PVMAS write patterns (read-only)")
    parser.add_argument("--site", default="hq", choices=("hq", "syp"))
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()
    data = mine(args.site)
    if args.json:
        print(json.dumps(data, default=str, indent=2))
        return 0
    print(f"Site: {data['site']}")
    print(f"Note-only PVMAS rows: {data['note_only_count']}")
    print(f"JOURMODE split: {data['jourmode_split']}")
    print(f"Max KCPN this month: {data.get('voucno_max_kcpn')}")
    print(f"Triggers: {data['triggers'] or 'none'}")
    print("\nBILLAMT vs SUM(AFTERTAX) sample:")
    for row in data["billamt_check"]:
        print(f"  {row['NOTENO']} billamt={row['BILLAMT']} sum={row['sum_aftertax']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
