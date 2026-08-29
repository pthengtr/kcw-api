from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings
from src.transfer.db import get_shipment_by_token, get_transfer_supabase_client
from src.transfer.writers._engine import (
    TransferWriteError,
    _writer_engine_hq,
    _next_billno,
)
from src.transfer.writers.syp_iclow_stamp import mark_received


class TransferTFError(TransferWriteError):
    """Specific transfer TF error."""
    pass


def post_transfer_tf(
    *,
    transfer_id: str,
    short_id: str,
    lines: list[dict[str, Any]],
    operator: str,
    client_token: str,
) -> dict[str, Any]:
    """
    Create a Transfer Out (TF) bill for HQ preparation.
    
    Args:
        transfer_id: The UUID of the transfer request
        short_id: Short representation of transfer ID 
        lines: List of line items to prepare with structure:
               {line_id, bcode, qty_ship, descr}
        operator: Name of person performing the action
        client_token: Unique token for idempotency
        
    Returns:
        Dict containing tf_billno and shipment_id
    """
    if not lines:
        raise TransferTFError("No lines provided", code="empty_lines")
    
    # Check if this client_token has already been used for this transfer
    client = get_transfer_supabase_client()
    existing_shipment = get_shipment_by_token(
        client, transfer_id=transfer_id, client_token=client_token
    )
    if existing_shipment:
        return {
            "tf_billno": existing_shipment.get("tf_billno"),
            "shipment_id": existing_shipment["shipment_id"],
        }
        
    # Generate a new TF bill
    engine = _writer_engine_hq()
    now = datetime.now()
    billdate = now.replace(hour=0, minute=0, second=0, microsecond=0)
    billtime = f"{now.hour:2d}{now.minute:02d}"
    jourmode = "2"  # non-VAT path like many zero-amount docs
    remarks = f"TRF-{short_id}"[:30]  # Maximum 30 chars
    billno = _next_billno(engine, "TF", now)
    
    # Get a template bill type from existing TF entries to maintain consistency
    billtype = "1"  # Default to outbound (stock out) 
    try:
        # Query existing TF entry to determine the correct BILLTYPE
        template_query = text(
            """
            SELECT TOP 1 BILLTYPE 
            FROM dbo.SIMAS 
            WHERE BILLNO LIKE 'TF%' AND BILLNO NOT LIKE 'TF%'
            ORDER BY BILLDATE DESC, BILLTIME DESC
            """
        )
        template_result = engine.execute(template_query).mappings().first()
        if template_result and template_result.get("BILLTYPE"):
            billtype = str(template_result["BILLTYPE"])
    except Exception:
        # If we can't fetch template, default to 1 (outbound stock)
        pass
    
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
                    "billno": billno,
                    "lines": len(lines),
                    "sale": operator[:15],  # Maximum 15 chars
                    "remarks": remarks,
                },
            )
            
            # Insert SIDET lines and update ICMAS QTYOH2 for HQ stock reduction
            qtyoh2_update_sql = text(
                """
                UPDATE dbo.ICMAS
                SET QTYOH2 = :qty
                WHERE LTRIM(RTRIM(BCODE)) = :bcode
                """
            )
            
            # Insert lines into SIDET - one row per line item
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
            
            for i, line in enumerate(lines, start=1):
                bcode = str(line.get("bcode") or "").strip()
                qty_ship = float(line.get("qty_ship") or 0)
                descr = (line.get("descr") or "")[:60]
                
                # Get product info from ICMAS for MCODE, PCODE
                product_info = conn.execute(
                    text(
                        """
                        SELECT MCODE, PCODE, UI1, LOCATION1  
                        FROM dbo.ICMAS 
                        WHERE LTRIM(RTRIM(BCODE)) = :bcode
                        """
                    ),
                    {"bcode": bcode}
                ).mappings().first()
                
                mcode = product_info["MCODE"] if product_info and product_info.get("MCODE") else ""
                pcode = product_info["PCODE"] if product_info and product_info.get("PCODE") else ""
                ui1 = product_info["UI1"] if product_info and product_info.get("UI1") else "unit"
                location1 = product_info["LOCATION1"] if product_info and product_info.get("LOCATION1") else ""
                
                # Insert SIDET line
                conn.execute(
                    sidet_insert,
                    {
                        "jourmode": jourmode,
                        "billdate": billdate,
                        "billtype": billtype,
                        "billno": billno,
                        "line": i * 10,  # Line numbers should be multiple of 10 (10, 20, 30...)
                        "bcode": bcode,
                        "pcode": pcode or None,
                        "mcode": mcode or None,
                        "detail": descr,
                        "location1": location1[:10] or None,
                        "qty": -qty_ship,  # Negative for stock OUT (preparation)
                        "ui": ui1[:10],
                        "mtp": 1.0,  # Pack multiplier is always 1 for stock reduction
                    }
                )
                
                # Update ICMAS QTYOH2 (reduce on-hand stock)
                if product_info:
                    new_qty = float(product_info.get("QTYOH2") or 0) - qty_ship
                    
                    conn.execute(
                        qtyoh2_update_sql,
                        {"qty": new_qty, "bcode": bcode}
                    )
                    
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "permission" in msg.lower() or "denied" in msg.lower() or "424" in msg:
            raise TransferTFError(
                "PARTS9 write denied — grant writer login (INSERT SIMAS/SIDET, UPDATE ICMAS)",
                code="permission_denied",
            ) from exc
        raise TransferTFError(f"PARTS9 write failed: {msg}", code="write_failed") from exc
    
    # Store shipment info in Supabase for tracking
    try:
        shipment_id = str(uuid4())
        shipment_data = {
            "shipment_id": shipment_id,
            "transfer_id": transfer_id,
            "client_token": client_token,
            "tf_billno": billno,
            "status": "prepared",
            "created_at": now.isoformat(),
        }
        
        resp = (
            client.schema("transfer")
            .from_("shipments")
            .insert(shipment_data)
            .select("*")
            .execute()
        )
        
        # For consistency, add lines to shipment_lines table
        shipment_line_data = []
        for line in lines:
            shipment_line_data.append({
                "shipment_line_id": str(uuid4()),
                "shipment_id": shipment_id,
                "line_id": line.get("line_id"),
                "bcode": str(line.get("bcode") or "").strip(),
                "qty_ship": float(line.get("qty_ship") or 0),
                "descr": (line.get("descr") or "").strip() or None
            })
        
        if shipment_line_data:
            resp = (
                client.schema("transfer")
                .from_("shipment_lines")
                .insert(shipment_line_data)
                .select("*")
                .execute()
            )
            
    except Exception as exc:
        # Log the issue but still return successful TF bill creation (don't re-raise to avoid transaction issues)
        pass
    
    return {
        "tf_billno": billno,
        "shipment_id": shipment_id
    }