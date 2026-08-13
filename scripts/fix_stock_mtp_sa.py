"""One-off: post corrective SA bills after MTP bug (stock-check stamped MTP2).

Targets last counted qty from local drafts. Run from kcw-api cwd with .env loaded.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.stock_check.config import get_stock_check_settings
from src.stock_check.parts9 import clear_parts9_engine_cache, get_product_by_bcode
from src.stock_check.sa_writer import post_stock_adjustment

# bcode -> target QTYOH2 (last physical count in smallest units)
CORRECTIONS = {
    "15010490": 10.0,  # counted 10 twice; live blown to 18733 via MTP=80
    "15014180": 61.0,  # counted 61; live blown to 277 via MTP=55
    "13050418": 122.0,  # counted 122; live became 113 via MTP=10
}


def main() -> int:
    settings = get_stock_check_settings()
    clear_parts9_engine_cache()
    print(f"branch={settings.stock_check_branch} writer={settings.pos_mssql_writer_username!r}")

    results = []
    for bcode, target in CORRECTIONS.items():
        product = get_product_by_bcode(bcode)
        if not product:
            print(f"FAIL {bcode}: not found in ICMAS")
            return 1
        live = float(product.qtyoh2)
        variance = target - live
        print(
            f"\n{bcode}: live={live} target={target} variance={variance} "
            f"UI1={product.ui1!r} MTP2={product.mtp2}"
        )
        if abs(variance) < 1e-9:
            print("  skip (already at target)")
            results.append((bcode, live, target, None, "skip"))
            continue
        posted = post_stock_adjustment(
            settings=settings,
            product=product,
            variance=variance,
            operator_name="fix-MTP",
            approver_name="auto",
        )
        print(
            f"  posted {posted.billno} type={posted.billtype} "
            f"qty_signed={posted.qty_signed} new_qtyoh2={posted.new_qtyoh2}"
        )
        results.append((bcode, live, target, posted.billno, posted.new_qtyoh2))

    clear_parts9_engine_cache()
    print("\n=== Verify live QTYOH2 ===")
    ok = True
    for bcode, target in CORRECTIONS.items():
        product = get_product_by_bcode(bcode)
        live = float(product.qtyoh2) if product else None
        match = product is not None and abs(live - target) < 1e-6
        print(f"  {bcode}: QTYOH2={live} target={target} {'OK' if match else 'MISMATCH'}")
        if not match:
            ok = False

        # Confirm latest SC SA line for this bcode has MTP=1
        from sqlalchemy import text
        from src.stock_check.parts9 import get_parts9_engine

        eng = get_parts9_engine(writer=False)
        with eng.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1
                      LTRIM(RTRIM(m.BILLNO)) AS billno,
                      d.QTY, d.UI, d.MTP, m.REMARKS
                    FROM dbo.SIDET d
                    INNER JOIN dbo.SIMAS m
                      ON d.BILLNO=m.BILLNO AND d.BILLDATE=m.BILLDATE
                     AND d.BILLTYPE=m.BILLTYPE AND d.JOURMODE=m.JOURMODE
                    WHERE LTRIM(RTRIM(d.BCODE)) = :bcode
                      AND m.REMARKS LIKE 'SC:%'
                    ORDER BY m.BILLDATE DESC, m.BILLTIME DESC, m.BILLNO DESC
                    """
                ),
                {"bcode": bcode},
            ).mappings().first()
        print(f"    latest SC line: {dict(row) if row else None}")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
