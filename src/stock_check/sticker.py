"""Print one product barcode sticker to the shop TSC TE310 (raw TSPL :9100).

Reuses the same label layout / TSPL builder as transfer receive stickers.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.stock_check.config import get_stock_check_settings
from src.stock_check.parts9 import get_parts9_engine
from src.transfer.sticker import (
    PRINTER_PORT,
    build_batch_tspl,
    clamp_sticker_qty,
    is_lan_printer_host,
    label_from_icmas,
    normalize_printer_model,
    send_tspl,
    validate_batch,
)

logger = logging.getLogger(__name__)

MAX_PRINT_QTY = 50


def fetch_sticker_catalog(
    bcodes: list[str],
    *,
    engine: Engine | None = None,
) -> dict[str, dict[str, Any]]:
    """ICMAS fields for the 5×3.5 cm sticker from this branch's PARTS9."""
    codes = sorted({(c or "").strip() for c in bcodes if (c or "").strip()})
    if not codes:
        return {}
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    sql = text(
        f"""
        SELECT
          LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS bcode,
          LTRIM(RTRIM(COALESCE(DESCR, ''))) AS descr,
          LTRIM(RTRIM(COALESCE(BRAND, ''))) AS brand,
          LTRIM(RTRIM(COALESCE(MODEL, ''))) AS model,
          LTRIM(RTRIM(COALESCE(UI1, ''))) AS ui1,
          LTRIM(RTRIM(COALESCE(LOCATION1, ''))) AS location1,
          LTRIM(RTRIM(COALESCE(LOCATION2, ''))) AS location2,
          LTRIM(RTRIM(COALESCE(MCODE, ''))) AS mcode,
          LTRIM(RTRIM(COALESCE(PCODE, ''))) AS pcode,
          LTRIM(RTRIM(COALESCE(VENDOR, ''))) AS vendor,
          COSTNET,
          PRICE1
        FROM dbo.ICMAS WITH (NOLOCK)
        WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) IN ({placeholders})
        """
    )
    out: dict[str, dict[str, Any]] = {}
    try:
        eng = engine or get_parts9_engine(writer=False)
        with eng.connect() as conn:
            rows = conn.execute(sql, params).mappings().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("stock-check sticker ICMAS fetch failed: %s", exc)
        return {}
    for row in rows:
        bcode = (row.get("bcode") or "").strip()
        if not bcode:
            continue
        out[bcode] = {
            "bcode": bcode,
            "descr": (row.get("descr") or "").strip(),
            "brand": (row.get("brand") or "").strip(),
            "model": (row.get("model") or "").strip(),
            "ui1": (row.get("ui1") or "").strip(),
            "location1": (row.get("location1") or "").strip(),
            "location2": (row.get("location2") or "").strip(),
            "mcode": (row.get("mcode") or "").strip(),
            "pcode": (row.get("pcode") or "").strip(),
            "vendor": (row.get("vendor") or "").strip(),
            "costnet": row.get("COSTNET"),
            "price1": row.get("PRICE1"),
        }
    return out


def print_product_sticker(
    bcode: str,
    *,
    qty: int = 1,
    host: str | None = None,
    port: int | None = None,
    printer_model: str | None = None,
    site: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Build TSPL for one SKU and send it to the LAN barcode printer."""
    settings = get_stock_check_settings()
    code = (bcode or "").strip()
    if not code:
        raise ValueError("ไม่พบรหัสสินค้า")
    copies = clamp_sticker_qty(qty)
    if copies <= 0:
        raise ValueError("ระบุจำนวนดวงอย่างน้อย 1")
    if copies > MAX_PRINT_QTY:
        raise ValueError(f"พิมพ์ได้สูงสุด {MAX_PRINT_QTY} ดวงต่อครั้ง")

    catalog = fetch_sticker_catalog([code], engine=engine)
    row = catalog.get(code)
    if not row:
        raise ValueError(f"ไม่พบสินค้า {code} ในระบบ")

    branch = (site or settings.stock_check_branch or "HQ").strip().upper()
    model = normalize_printer_model(
        printer_model or settings.stock_check_sticker_printer_model or "te310"
    )
    labels = [label_from_icmas(row, qty=copies, site=branch)]
    problem = validate_batch(labels)
    if problem:
        raise ValueError(problem)

    payload = build_batch_tspl(labels, printer_model=model)
    target = (host if host is not None else settings.stock_check_sticker_printer_host or "").strip()
    if not target:
        raise ValueError("ยังไม่ได้ตั้งค่า IP เครื่องพิมพ์ (STOCK_CHECK_STICKER_PRINTER_HOST)")
    if not is_lan_printer_host(target):
        raise ValueError("IP เครื่องพิมพ์ต้องอยู่ในวง LAN / Tailscale")
    dest_port = int(
        port if port is not None else (settings.stock_check_sticker_printer_port or PRINTER_PORT)
    )
    send_tspl(payload, host=target, port=dest_port)
    return {
        "status": "sent",
        "bcode": code,
        "printer_model": model,
        "host": target,
        "port": dest_port,
        "copies": copies,
    }
