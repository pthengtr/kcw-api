from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.transfer.db import get_shipment_by_token, get_transfer_supabase_client
from src.transfer.direction import ship_billno_prefix
from src.transfer.writers._engine import (
    TransferWriteError,
    TRANSFER_BOOKNO,
    next_simas_billno,
    transfer_write_permission_hint,
    writer_engine_for_branch,
    _fetch_icmas_row,
)


class TransferShipError(TransferWriteError):
    pass


def post_transfer_ship(
    *,
    from_branch: str,
    transfer_id: str,
    short_id: str,
    lines: list[dict[str, Any]],
    operator: str,
    client_token: str,
) -> dict[str, Any]:
    """Create SIMAS/SIDET ship bill at from_branch (TF or 3TF)."""
    if not lines:
        raise TransferShipError("No lines provided", code="empty_lines")

    client = get_transfer_supabase_client()
    existing = get_shipment_by_token(
        client, transfer_id=transfer_id, client_token=client_token
    )
    if existing:
        billno = existing.get("ship_billno") or existing.get("tf_billno")
        return {
            "ship_billno": billno,
            "tf_billno": billno,
            "shipment_id": existing["shipment_id"],
        }

    engine = writer_engine_for_branch(from_branch)
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:02d}{now.minute:02d}"
    jourmode = "2"
    remarks = f"TRF-{short_id}"[:30]
    billtype = "1"

    try:
        with engine.begin() as conn:
            billno = next_simas_billno(from_branch=from_branch, when=now)
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.SIMAS (
                      JOURMODE, JOURTYPE, JOURDATE, JOURTIME, DEPTNO, BOOKNO,
                      BILLTYPE, BILLDATE, BILLTIME, BILLNO, LINES, TAXIC,
                      DISCOUNT, DEDUCT, BEFORETAX, VAT, TAX, AFTERTAX, EXEMPT, SVCCHG,
                      PAID, CASHED, CASHAMT, CHKAMT, DUEAMT,
                      SALE, REMARKS, POSTED1, POSTED2, CANCELED, DONE
                    ) VALUES (
                      :jourmode, 'SJ', :billdate, :jourtime, '1', :bookno,
                      :billtype, :billdate, :billtime, :billno, :lines, 'N',
                      0, 0, 0, 0, 0, 0, 0, 0,
                      'Y', 'Y', 0, 0, 0,
                      :sale, :remarks, 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "bookno": TRANSFER_BOOKNO,
                    "billdate": billdate,
                    "jourtime": billtime,
                    "billtime": billtime,
                    "billtype": billtype,
                    "billno": billno,
                    "lines": len(lines),
                    "sale": operator[:15],
                    "remarks": remarks,
                },
            )

            sidet_insert = text(
                """
                INSERT INTO dbo.SIDET (
                  JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
                  LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
                  STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
                  QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
                  PAID, DONE, CANCELED
                ) VALUES (
                  :jourmode, 'SJ', :billdate, :billtype, :billdate, :billno,
                  :line, 1, :bcode, :pcode, :mcode, :detail, 'Y', :location1,
                  1, 'N', 'N', 'N', 'N',
                  :qty, :ui, :mtp, 0, 0, 0, 0,
                  'N', 'N', 'N'
                )
                """
            )
            qtyoh2_update = text(
                """
                UPDATE dbo.ICMAS SET QTYOH2 = :qty
                WHERE LTRIM(RTRIM(BCODE)) = :bcode
                """
            )

            for i, line in enumerate(lines, start=1):
                bcode = str(line.get("bcode") or "").strip()
                qty_ship = float(line.get("qty_ship") or 0)
                if qty_ship <= 0:
                    raise TransferShipError("qty_ship must be > 0", code="invalid_qty")
                descr = (line.get("descr") or "")[:60]
                product = _fetch_icmas_row(conn, bcode)
                conn.execute(
                    sidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": billno,
                        "line": i * 10,
                        "bcode": bcode,
                        "pcode": (product or {}).get("PCODE") or None,
                        "mcode": (product or {}).get("MCODE") or None,
                        "detail": descr,
                        "location1": (str((product or {}).get("LOCATION1") or "")[:10] or None),
                        # TF ship leg: SIMAS BILLTYPE 1, always positive line QTY (not SA +/- sign).
                        "qty": qty_ship,
                        "ui": str((product or {}).get("UI1") or "unit")[:10],
                        "mtp": 1.0,
                    },
                )
                if product:
                    new_qty = float(product.get("QTYOH2") or 0) - qty_ship
                    conn.execute(qtyoh2_update, {"qty": new_qty, "bcode": bcode})
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(exc, branch=from_branch, tables="SIMAS/SIDET/ICMAS")
        if hint:
            raise TransferShipError(hint, code="permission_denied") from exc
        raise TransferShipError(str(exc), code="sql_error") from exc

    prefix = ship_billno_prefix(from_branch=from_branch)
    if not billno.startswith(prefix):
        pass  # billno from generator

    return {
        "ship_billno": billno,
        "tf_billno": billno,
    }


# Back-compat alias
class TransferTFError(TransferShipError):
    pass


def post_transfer_tf(
    *,
    transfer_id: str,
    short_id: str,
    lines: list[dict[str, Any]],
    operator: str,
    client_token: str,
    from_branch: str = "HQ",
) -> dict[str, Any]:
    return post_transfer_ship(
        from_branch=from_branch,
        transfer_id=transfer_id,
        short_id=short_id,
        lines=lines,
        operator=operator,
        client_token=client_token,
    )
