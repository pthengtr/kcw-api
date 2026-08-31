from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.transfer.writers._engine import (
    TransferWriteError,
    next_pimas_billno,
    transfer_write_permission_hint,
    writer_engine_for_branch,
    _fetch_icmas_row,
)


class TransferReceiveError(TransferWriteError):
    pass


def post_transfer_receive(
    *,
    to_branch: str,
    from_branch: str,
    shipment: dict[str, Any],
    lines_to_receive: list[dict[str, Any]],
    operator: str,
    client_token: str,
) -> dict[str, Any]:
    """Create PIMAS/PIDET receive bill at to_branch (TF or 3TF)."""
    if not lines_to_receive:
        raise TransferReceiveError("No lines to receive", code="empty_lines")

    for line in lines_to_receive:
        if float(line.get("qty_receive", 0)) <= 0:
            raise TransferReceiveError("Invalid quantity to receive", code="invalid_quantity")

    if shipment.get("posted_at"):
        return {"status": "already_processed", "receive_billno": shipment.get("receive_billno")}

    ship_billno = shipment.get("ship_billno") or shipment.get("tf_billno")
    if not ship_billno:
        raise TransferReceiveError("No ship bill on shipment", code="missing_ship_bill")

    engine = writer_engine_for_branch(to_branch)
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:02d}{now.minute:02d}"
    jourmode = "2"
    remarks = f"RCV-{str(ship_billno)[:24]}"[:30]
    billtype = "2"

    try:
        with engine.begin() as conn:
            billno = next_pimas_billno(
                from_branch=from_branch, to_branch=to_branch, when=now
            )
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.PIMAS (
                      JOURMODE, JOURTYPE, JOURDATE, JOURTIME, DEPTNO, BOOKNO,
                      BILLTYPE, BILLDATE, BILLTIME, BILLNO, LINES, TAXIC,
                      DISCOUNT, DEDUCT, BEFORETAX, VAT, TAX, AFTERTAX, EXEMPT, SVCCHG,
                      PAID, CASHED, CASHAMT, CHKAMT, DUEAMT,
                      SALE, REMARKS, POSTED1, POSTED2, CANCELED, DONE
                    ) VALUES (
                      :jourmode, 'PJ', :billdate, :jourtime, '1', '1',
                      :billtype, :billdate, :billtime, :billno, :lines, 'N',
                      0, 0, 0, 0, 0, 0, 0, 0,
                      'N', 'N', 0, 0, 0,
                      :sale, :remarks, 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "billdate": billdate,
                    "jourtime": billtime,
                    "billtime": billtime,
                    "billtype": billtype,
                    "billno": billno,
                    "lines": len(lines_to_receive),
                    "sale": operator[:15],
                    "remarks": remarks,
                },
            )

            pidet_insert = text(
                """
                INSERT INTO dbo.PIDET (
                  JOURMODE, JOURTYPE, JOURDATE, BILLTYPE, BILLDATE, BILLNO,
                  LINE, ITEMNO, BCODE, PCODE, MCODE, DETAIL, WHNUMBER, LOCATION1,
                  STATUS, SERIAL, TAXIC, EXMPT, ISVAT,
                  QTY, UI, MTP, PRICE, XPRICE, VAT, AMOUNT,
                  PAID, DONE, CANCELED
                ) VALUES (
                  :jourmode, 'PJ', :billdate, :billtype, :billdate, :billno,
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

            for i, line in enumerate(lines_to_receive, start=1):
                bcode = str(line.get("bcode") or "").strip()
                qty_recv = float(line.get("qty_receive") or 0)
                descr = (line.get("descr") or "")[:60]
                product = _fetch_icmas_row(conn, bcode)
                if not product:
                    continue
                conn.execute(
                    pidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": billno,
                        "line": i * 10,
                        "bcode": bcode,
                        "pcode": product.get("PCODE") or None,
                        "mcode": product.get("MCODE") or None,
                        "detail": descr,
                        "location1": str(product.get("LOCATION1") or "")[:10] or None,
                        "qty": qty_recv,
                        "ui": str(product.get("UI1") or "unit")[:10],
                        "mtp": 1.0,
                    },
                )
                new_qty = float(product.get("QTYOH2") or 0) + qty_recv
                conn.execute(qtyoh2_update, {"qty": new_qty, "bcode": bcode})
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(exc, branch=to_branch, tables="PIMAS/PIDET/ICMAS")
        if hint:
            raise TransferReceiveError(hint, code="permission_denied") from exc
        raise TransferReceiveError(str(exc), code="sql_error") from exc

    return {
        "status": "received",
        "receive_billno": billno,
        "ship_billno": ship_billno,
        "client_token": client_token,
    }
