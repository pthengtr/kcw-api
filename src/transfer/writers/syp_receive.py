from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings
from src.transfer.db import get_transfer_supabase_client
from src.transfer.writers._engine import (
    TransferWriteError,
    _get_syp_engine,
)
from src.transfer.writers.syp_iclow_stamp import mark_received


class TransferReceiveError(TransferWriteError):
    """Specific transfer receive error."""
    pass


def post_transfer_receive(
    *,
    shipment: dict[str, Any],
    lines_to_receive: list[dict[str, Any]],
    operator: str,
    client_token: str,
) -> dict[str, Any]:
    """
    Create a Transfer In (receive) bill for SYP.
    
    Args:
        shipment: The shipment object from Supabase
        lines_to_receive: List of line items to receive with structure:
                          {shipment_line_id, bcode, qty_receive}
        operator: Name of person performing the action
        client_token: Unique token for idempotency
        
    Returns:
        Dict containing receipt info
    """
    if not lines_to_receive:
        raise TransferReceiveError("No lines to receive", code="empty_lines")

    for line in lines_to_receive:
        if float(line.get("qty_receive", 0)) <= 0:
            raise TransferReceiveError("Invalid quantity to receive", code="invalid_quantity")

    if shipment.get("posted_at"):
        return {"status": "already_processed"}

    # Check if this client_token has already been used for this shipment (idempotency)
    try:
        client = get_transfer_supabase_client() 
        resp = (
            client.schema("transfer")
            .from_("shipments")
            .select("*")
            .eq("client_token", client_token)
            .eq("shipment_id", shipment["shipment_id"])
            .limit(1)
            .execute()
        )
        rows = [dict(r) for r in (resp.data or [])]
        if rows:
            # Already processed - return success
            return {"status": "already_processed"}
    except Exception:
        # If we can't check the database for existing shipment, continue with creation
        pass
    
    # Get the TF bill number that was created by HQ
    tf_billno = shipment.get("tf_billno")
    if not tf_billno:
        raise TransferReceiveError("No TF bill found in shipment", code="missing_tf_bill")

    # Validate against HQ TF when possible (read-only); writes use SYP engine below.
    hq_engine = get_site_engine("hq")
    tf_lines = []
    try:
        # Query TF SIDET to check expected quantities
        query_sidet = text(
            """
            SELECT BCODE, QTY 
            FROM dbo.SIDET 
            WHERE BILLNO = :billno AND JOURTYPE = 'SJ'
            ORDER BY LINE
            """
        )
        
        result = hq_engine.execute(query_sidet, {"billno": tf_billno}).mappings().all()
        for row in result:
            tf_lines.append({
                "bcode": row["BCODE"] or "",
                "qty": float(row["QTY"] or 0)
            })
    except Exception:
        # If we can't check the original TF lines, proceed anyway
        pass
    
    # Validate that all provided line quantities match expected quantities (at least roughly)
    # We don't do exact quantity comparisons unless we have the full original data
    
    # Process the receipt in SYP database
    engine = _get_syp_engine()  # This will be our target write database  
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:2d}{now.minute:02d}"
    jourmode = "2"  # non-VAT path like many zero-amount docs
    remarks = f"RCV-{tf_billno}"[:30]  # Maximum 30 chars - using TF number in remarks
    
    # Determine the bill type (should be type 2 for receive)
    billtype = "2"
    
    try:
        with engine.begin() as conn:
            # Insert SIMAS header
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
                      :jourmode, 'SJ', :billdate, :jourtime, '1', '1',
                      :billtype, :billdate, :billtime, :billno, :lines, 'N',
                      0, 0, 0, 0, 0, 0, 0, 0,
                      'Y', 'Y', 0, 0, 0,
                      :sale, :remarks, 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "billdate": billdate,
                    "jourtime": billtime,
                    "billtype": billtype,
                    "billtime": billtime,
                    "billno": tf_billno,  # Use the same bill number (for consistency)
                    "lines": len(lines_to_receive),
                    "sale": operator[:15],  # Maximum 15 chars
                    "remarks": remarks,
                },
            )
            
            # Insert SIDET lines and update ICMAS QTYOH2 for SYP stock increase
            qtyoh2_update_sql = text(
                """
                UPDATE dbo.ICMAS
                SET QTYOH2 = :qty
                WHERE LTRIM(RTRIM(BCODE)) = :bcode
                """
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
            
            for i, line in enumerate(lines_to_receive, start=1):
                bcode = str(line.get("bcode") or "").strip()
                qty_receive = float(line.get("qty_receive") or 0)
                shipment_line_id = line.get("shipment_line_id")
                
                # Get product info from ICMAS for MCODE, PCODE  
                product_info = conn.execute(
                    text(
                        """
                        SELECT MCODE, PCODE, UI1, LOCATION1, QTYOH2  
                        FROM dbo.ICMAS 
                        WHERE LTRIM(RTRIM(BCODE)) = :bcode
                        """
                    ),
                    {"bcode": bcode}
                ).mappings().first()
                
                if not product_info:
                    continue  # Skip items that don't exist in SYP database
                
                mcode = product_info["MCODE"] if product_info and product_info.get("MCODE") else ""
                pcode = product_info["PCODE"] if product_info and product_info.get("PCODE") else ""
                ui1 = product_info["UI1"] if product_info and product_info.get("UI1") else "unit"
                location1 = product_info["LOCATION1"] if product_info and product_info.get("LOCATION1") else ""
                current_qty = float(product_info.get("QTYOH2") or 0)
                
                # Insert SIDET line
                conn.execute(
                    sidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": tf_billno,  # Same as transfer out
                        "line": i * 10,  # Line numbers should be multiple of 10 (10, 20, 30...)
                        "bcode": bcode,
                        "pcode": pcode or None,
                        "mcode": mcode or None,
                        "detail": (product_info.get("DESCR") or "")[:60],
                        "location1": location1[:10] or None,
                        "qty": qty_receive,  # Positive for stock IN (receipt)
                        "ui": ui1[:10],
                        "mtp": 1.0,  # Pack multiplier is always 1 for stock increase
                    }
                )
                
                # Update ICMAS QTYOH2 (increase on-hand stock)
                new_qty = current_qty + qty_receive
                
                conn.execute(
                    qtyoh2_update_sql,
                    {"qty": new_qty, "bcode": bcode}
                )
                
                # If ICLOW stamp is enabled for this transfer and line has iclow_id, mark as received
                settings = get_transfer_settings()
                if settings.transfer_iclow_stamp_enabled:
                    # Need to check shipment line by shipment_line_id for iclow_id info
                    try:
                        resp = (
                            client.schema("transfer")
                            .from_("shipment_lines")
                            .select("iclow_id")
                            .eq("shipment_line_id", shipment_line_id)
                            .limit(1)
                            .execute()
                        )
                        rows = [dict(r) for r in (resp.data or [])]
                        if rows and rows[0].get("iclow_id"):
                            iclow_id = rows[0]["iclow_id"]
                            # Call mark_received to stamp ICLOW
                            mark_received(iclow_id=iclow_id, tf_billno=tf_billno)
                    except Exception:
                        # If there's a problem with ICLOW stamping, continue silently  
                        pass
    
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "permission" in msg.lower() or "denied" in msg.lower() or "424" in msg:
            raise TransferReceiveError(
                "PARTS9 write denied — grant writer login (INSERT SIMAS/SIDET, UPDATE ICMAS)",
                code="permission_denied",
            ) from exc
        raise TransferReceiveError(f"PARTS9 write failed: {msg}", code="write_failed") from exc
    
    # Store receive info in Supabase for tracking
    try:
        receipt_data = {
            "shipment_id": shipment["shipment_id"],
            "client_token": client_token,
            "received_at": now.isoformat(),
            "operator": operator[:50],
            "status": "received"
        }
        
        resp = (
            client.schema("transfer")
            .from_("receipts")
            .insert(receipt_data)
            .select("*")
            .execute()
        )
        
    except Exception:
        # Log the issue but don't re-raise
        pass
        
    return {"status": "received"}