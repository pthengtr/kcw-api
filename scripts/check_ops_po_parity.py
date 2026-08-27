#!/usr/bin/env python3
"""Read-only live PARTS9 parity checks for kcw-ops PO APIs.

Run from kcw-api repo root (needs PARTS9 connectivity):

  .venv/bin/python scripts/check_ops_po_parity.py
  .venv/bin/python scripts/check_ops_po_parity.py --site syp --days 30

Sign-off checklist (manual + this script):
  [ ] SYP PO list count for last 30d loads without error
  [ ] SYP prepare_status in {not_prepared, partially_prepared, prepared}
  [ ] HQ pending_receive / partially_received rows include rcvdno enrichment fields
  [ ] Account lookup for a known ACCTNO returns source apmas or po_only
  [ ] PI resolve for a known RCVDNO returns header+lines or clean 404 path
  [ ] Operators open via LINE สถานะใบสั่งซื้อ / Tailscale :8790 (kcw-v2 /po unchanged)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BKK = ZoneInfo("Asia/Bangkok")


def _window(days: int) -> tuple[str, str]:
    today = datetime.now(BKK).date()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", choices=("hq", "syp", "both"), default="both")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    from src.ops.account import get_account_detail
    from src.ops.iclow import list_iclow
    from src.ops.pi import get_pi_detail, resolve_pimas_billno
    from src.ops.po import get_po_lines, health_probes, list_purchase_orders
    from src.ops.tf_prepare import attach_header_prepare, rollup_prepare_status

    dfrom, dto = _window(args.days)
    sites = ["hq", "syp"] if args.site == "both" else [args.site]
    probes = health_probes()
    print(f"probes: {probes}")
    print(f"window: {dfrom} .. {dto}")
    errors: list[str] = []

    for site in sites:
        print(f"\n=== site={site.upper()} ===")
        try:
            data = list_purchase_orders(
                site=site, status="all", dfrom=dfrom, dto=dto, limit=args.limit, offset=0
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{site} list_purchase_orders: {exc}")
            print(f"FAIL list: {exc}")
            continue
        print(f"PO list count={data.get('count')} rows={len(data.get('rows') or [])} live={data.get('live')}")
        rows = data.get("rows") or []
        if site == "syp" and rows:
            attach_header_prepare(rows)
            bad = [
                r
                for r in rows
                if (r.get("prepare_status") or "not_prepared")
                not in ("not_prepared", "partially_prepared", "prepared")
            ]
            if bad:
                errors.append(f"syp prepare_status invalid: {bad[0].get('docno')}")
            prepared_n = sum(1 for r in rows if r.get("prepare_status") == "prepared")
            print(f"prepare rollup on page: prepared={prepared_n}/{len(rows)}")
            # sanity of rollup helper
            assert rollup_prepare_status(line_count=2, prepared_line_count=2, any_tf_line_count=2) == "prepared"
            sample = rows[0]
            try:
                detail = get_po_lines(site="syp", docno=sample["docno"])
                print(f"detail {sample['docno']}: lines={len(detail.get('lines') or [])}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"syp detail {sample.get('docno')}: {exc}")
            if sample.get("acctno"):
                try:
                    acct = get_account_detail(
                        acctno=sample["acctno"], site="syp", docno=sample.get("docno")
                    )
                    print(
                        f"account {sample['acctno']}: source={acct and acct.get('source')} "
                        f"name={acct and acct.get('acctname')}"
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"account: {exc}")

        for st in ("to_be_ordered", "pending_receive", "partially_received"):
            try:
                if st == "to_be_ordered":
                    ic = list_iclow(site=site, status=st, limit=args.limit, offset=0)
                else:
                    ic = list_iclow(
                        site=site, status=st, dfrom=dfrom, dto=dto, limit=args.limit, offset=0
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{site} iclow {st}: {exc}")
                print(f"FAIL iclow {st}: {exc}")
                continue
            ic_rows = ic.get("rows") or []
            print(f"iclow {st}: count={ic.get('count')} rows={len(ic_rows)}")
            if site == "hq" and st != "to_be_ordered" and ic_rows:
                sample = next((r for r in ic_rows if r.get("rcvdno")), None)
                if sample:
                    for key in ("pimas_matched_billno", "pimas_match_method", "pimas_link_missing"):
                        if key not in sample:
                            errors.append(f"hq iclow missing {key}")
                    rcvd = sample.get("rcvdno")
                    print(
                        f"  sample rcvdno={rcvd} match={sample.get('pimas_match_method')} "
                        f"bill={sample.get('pimas_matched_billno')} missing={sample.get('pimas_link_missing')}"
                    )
                    try:
                        resolved = resolve_pimas_billno(str(rcvd))
                        pi = get_pi_detail(billno_or_rcvdno=str(rcvd))
                        print(
                            f"  resolve={resolved and resolved.get('match_method')} "
                            f"pi_lines={len((pi or {}).get('lines') or []) if pi else 0}"
                        )
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"pi resolve {rcvd}: {exc}")

    if errors:
        print("\nPARITY FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nPARITY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
