#!/usr/bin/env python3
"""Read-only KSS mining for RVMAS/SIMAS/BRDET write rules (receive-notes service).

Usage:
  cd projects/kcw-api && .venv/bin/python scripts/mine_rvmas_write_rules.py [--site hq]
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


def _serialize(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        item = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = v
        out.append(item)
    return out


def mine(site: str) -> dict:
    eng = get_site_engine(site)
    out: dict = {"site": site.upper(), "tables": {}}
    with eng.connect() as conn:
        out["note_only_count"] = conn.execute(
            text(
                """
                SELECT COUNT(*) AS c FROM dbo.RVMAS
                WHERE NOTED = 'Y' AND ISNULL(VOUCED, 'N') = 'N'
                  AND ISNULL(CANCELED, 'N') <> 'Y'
                """
            )
        ).scalar()

        out["note_only_sample"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 8 NOTENO, NOTEDATE, ACCTNO, ACCTNAME, BILLCNT, BILLAMT,
                       JOURTYPE, JOURMODE, DEPTNO, BOOKNO, RCPTNO,
                       DISCOUNT, NETAMT, PAYAMT, PAID, CASHAMT, CHKAMT,
                       POSTED1, POSTED2, DONE, CANCELED, VOUCED, VOUCNO
                FROM dbo.RVMAS
                WHERE NOTED = 'Y' AND ISNULL(VOUCED, 'N') = 'N'
                ORDER BY NOTEDATE DESC
                """,
            )
        )

        out["voucher_sample"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 10 VOUCNO, VOUCDATE, NOTENO, ACCTNO, ACCTNAME, BILLCNT, BILLAMT,
                       DISCOUNT, NETAMT, PAYAMT, CHKAMT, CASHAMT, PAID, NOTED, VOUCED,
                       JOURTYPE, JOURMODE, RCPTNO
                FROM dbo.RVMAS
                WHERE VOUCED = 'Y' AND ISNULL(CANCELED, 'N') <> 'Y'
                ORDER BY VOUCDATE DESC
                """,
            )
        )

        out["voucno_prefix_patterns"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 40
                  CASE
                    WHEN VOUCNO LIKE 'RC%' THEN 'RC' + SUBSTRING(VOUCNO, 3, 4)
                    WHEN VOUCNO LIKE '[0-9][0-9][0-9][0-9]-%' THEN LEFT(VOUCNO, 4)
                    WHEN VOUCNO LIKE 'TR%' THEN 'TR' + SUBSTRING(VOUCNO, 3, 4)
                    ELSE LEFT(VOUCNO, 6)
                  END AS prefix_stem,
                  JOURMODE,
                  COUNT(*) AS c,
                  MAX(VOUCNO) AS max_no,
                  MIN(VOUCNO) AS min_no
                FROM dbo.RVMAS
                WHERE ISNULL(LTRIM(RTRIM(VOUCNO)), '') <> ''
                  AND VOUCDATE >= DATEADD(month, -6, GETDATE())
                GROUP BY
                  CASE
                    WHEN VOUCNO LIKE 'RC%' THEN 'RC' + SUBSTRING(VOUCNO, 3, 4)
                    WHEN VOUCNO LIKE '[0-9][0-9][0-9][0-9]-%' THEN LEFT(VOUCNO, 4)
                    WHEN VOUCNO LIKE 'TR%' THEN 'TR' + SUBSTRING(VOUCNO, 3, 4)
                    ELSE LEFT(VOUCNO, 6)
                  END,
                  JOURMODE
                ORDER BY c DESC
                """,
            )
        )

        out["voucno_max_current_month"] = _serialize(
            _rows(
                conn,
                """
                DECLARE @yy char(2) = RIGHT(CONVERT(varchar(4), YEAR(GETDATE()) + 543), 2);
                DECLARE @mm char(2) = RIGHT('0' + CONVERT(varchar(2), MONTH(GETDATE())), 2);
                SELECT
                  (SELECT MAX(VOUCNO) FROM dbo.RVMAS WHERE VOUCNO LIKE @yy + @mm + '-%') AS max_nonvat,
                  (SELECT MAX(VOUCNO) FROM dbo.RVMAS WHERE VOUCNO LIKE 'RC' + @yy + @mm + '-%') AS max_vat_rc,
                  (SELECT MAX(VOUCNO) FROM dbo.RVMAS WHERE VOUCNO LIKE 'TR' + @yy + @mm + '-%') AS max_tr,
                  @yy + @mm AS yymm
                """,
            )
        )

        out["jourtype_split"] = _serialize(
            _rows(
                conn,
                """
                SELECT JOURTYPE, JOURMODE,
                       SUM(CASE WHEN NOTED='Y' AND ISNULL(VOUCED,'N')='N' THEN 1 ELSE 0 END) AS note_only,
                       SUM(CASE WHEN VOUCED='Y' THEN 1 ELSE 0 END) AS vouchered,
                       COUNT(*) AS c
                FROM dbo.RVMAS
                WHERE ISNULL(CANCELED,'N') <> 'Y'
                GROUP BY JOURTYPE, JOURMODE
                ORDER BY c DESC
                """,
            )
        )

        out["simas_note_link"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 5 r.NOTENO, r.ACCTNO, r.BILLAMT, r.BILLCNT,
                       (SELECT SUM(s.AFTERTAX) FROM dbo.SIMAS s
                        WHERE LTRIM(RTRIM(s.ACCTNO)) = LTRIM(RTRIM(r.ACCTNO))
                          AND LTRIM(RTRIM(s.NOTENO)) = LTRIM(RTRIM(r.NOTENO))) AS sum_aftertax,
                       (SELECT COUNT(*) FROM dbo.SIMAS s
                        WHERE LTRIM(RTRIM(s.ACCTNO)) = LTRIM(RTRIM(r.ACCTNO))
                          AND LTRIM(RTRIM(s.NOTENO)) = LTRIM(RTRIM(r.NOTENO))) AS bill_cnt
                FROM dbo.RVMAS r
                WHERE r.NOTED = 'Y' AND ISNULL(r.VOUCED, 'N') = 'N' AND r.BILLCNT > 0
                ORDER BY r.NOTEDATE DESC
                """,
            )
        )

        out["simas_voucher_stamp"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 8
                  r.VOUCNO, r.JOURMODE, r.PAYAMT, r.NETAMT, r.BILLAMT,
                  s.BILLNO, s.AFTERTAX, s.PAID, s.PAYSTAT, s.NOTENO, s.VOUCNO2, s.CASHED, s.JOURMODE
                FROM dbo.RVMAS r
                JOIN dbo.SIMAS s
                  ON LTRIM(RTRIM(s.VOUCNO2)) = LTRIM(RTRIM(r.VOUCNO))
                WHERE r.VOUCED = 'Y'
                ORDER BY r.VOUCDATE DESC
                """,
            )
        )

        out["partial_pay_candidates"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 20 BILLNO, ACCTNO, AFTERTAX, PAID, PAYSTAT, NOTENO, VOUCNO2, VOUCNO1,
                       CASHED, JOURMODE, DUEDATE
                FROM dbo.SIMAS
                WHERE ISNULL(CANCELED,'N') <> 'Y'
                  AND ISNULL(CASHED,'Y') = 'N'
                  AND ISNULL(PAID,'N') = 'N'
                  AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                  AND ISNULL(LTRIM(RTRIM(NOTENO)), '') <> ''
                ORDER BY BILLDATE DESC
                """,
            )
        )

        out["open_credit_bills_sample"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 10 BILLNO, BILLDATE, ACCTNO, ACCTNAME, AFTERTAX, DUEDATE,
                       PAID, PAYSTAT, NOTENO, VOUCNO2, CASHED, JOURMODE, BILLTYPE
                FROM dbo.SIMAS
                WHERE ISNULL(CANCELED,'N') <> 'Y'
                  AND ISNULL(CASHED,'Y') = 'N'
                  AND ISNULL(PAID,'N') = 'N'
                  AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                  AND JOURMODE IN ('1','2')
                ORDER BY BILLDATE DESC
                """,
            )
        )

        out["brdet_sample"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 15 VOUCNO, VOUCDATE, CHKNO, CHKDATE, CHKAMT, BANKNAME, ACCTNO,
                       PAYTYPE, JOURTYPE, STATUS, CANCELED
                FROM dbo.BRDET
                WHERE ISNULL(CANCELED, 'N') <> 'Y'
                ORDER BY VOUCDATE DESC
                """,
            )
        )

        out["brdet_by_channel"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 30
                  CASE
                    WHEN ISNULL(LTRIM(RTRIM(BANKNAME)),'') = '' AND ISNULL(LTRIM(RTRIM(ACCTNO)),'') = ''
                      THEN 'cash_like'
                    WHEN CHKNO LIKE N'%โอน%' OR CHKNO = 'โอน' THEN 'transfer'
                    WHEN ISNULL(LTRIM(RTRIM(CHKNO)),'') <> '' THEN 'cheque_or_ref'
                    ELSE 'other'
                  END AS channel_guess,
                  JOURTYPE, PAYTYPE, COUNT(*) AS c,
                  MAX(VOUCNO) AS sample_voucno,
                  MAX(BANKNAME) AS sample_bank,
                  MAX(ACCTNO) AS sample_gl
                FROM dbo.BRDET
                WHERE ISNULL(CANCELED,'N') <> 'Y'
                  AND VOUCDATE >= DATEADD(month, -6, GETDATE())
                GROUP BY
                  CASE
                    WHEN ISNULL(LTRIM(RTRIM(BANKNAME)),'') = '' AND ISNULL(LTRIM(RTRIM(ACCTNO)),'') = ''
                      THEN 'cash_like'
                    WHEN CHKNO LIKE N'%โอน%' OR CHKNO = 'โอน' THEN 'transfer'
                    WHEN ISNULL(LTRIM(RTRIM(CHKNO)),'') <> '' THEN 'cheque_or_ref'
                    ELSE 'other'
                  END,
                  JOURTYPE, PAYTYPE
                ORDER BY c DESC
                """,
            )
        )

        out["multi_brdet_per_voucher"] = _serialize(
            _rows(
                conn,
                """
                SELECT TOP 10 VOUCNO, COUNT(*) AS lines, SUM(CHKAMT) AS sum_amt
                FROM dbo.BRDET
                WHERE ISNULL(CANCELED,'N') <> 'Y'
                GROUP BY VOUCNO
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                """,
            )
        )

        for table in ("RVMAS", "SIMAS", "BRDET", "ARMAS"):
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

        out["triggers"] = _serialize(
            _rows(
                conn,
                """
                SELECT t.name AS table_name, tr.name AS trigger_name
                FROM sys.triggers tr
                JOIN sys.tables t ON tr.parent_id = t.object_id
                WHERE t.name IN ('RVMAS', 'SIMAS', 'BRDET')
                """,
            )
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine KSS RVMAS write patterns (read-only)")
    parser.add_argument("--site", default="hq", choices=("hq", "syp"))
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--out", default="", help="Write JSON to path")
    args = parser.parse_args()
    data = mine(args.site)
    payload = json.dumps(data, default=str, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    if args.json or args.out:
        if args.json:
            print(payload)
        else:
            print(f"Wrote {args.out}")
        if not args.json:
            print(f"Site: {data['site']}")
            print(f"Note-only RVMAS: {data['note_only_count']}")
            print(f"Prefix patterns: {data['voucno_prefix_patterns'][:8]}")
            print(f"Max current month: {data['voucno_max_current_month']}")
            print(f"JOURTYPE: {data['jourtype_split'][:8]}")
            print(f"Triggers: {data['triggers'] or 'none'}")
        return 0
    print(f"Site: {data['site']}")
    print(f"Note-only RVMAS rows: {data['note_only_count']}")
    print(f"JOURTYPE/MODE: {data['jourtype_split'][:10]}")
    print(f"Max this month: {data['voucno_max_current_month']}")
    print(f"Prefix patterns (top): {data['voucno_prefix_patterns'][:10]}")
    print(f"BRDET channels: {data['brdet_by_channel'][:10]}")
    print(f"Multi BRDET: {data['multi_brdet_per_voucher'][:5]}")
    print(f"Triggers: {data['triggers'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
