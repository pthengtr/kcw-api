"""Create a minimal HQ ICMAS product row from the receive screen."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError
from src.transfer.writers._engine import (
    transfer_write_permission_hint,
    writer_engine_for_branch,
)


def _main_from_bcode(bcode: str) -> int | None:
    digits = "".join(ch for ch in bcode if ch.isdigit())
    if len(digits) >= 2:
        try:
            return int(digits[:2])
        except ValueError:
            return None
    return None


def create_product(payload: dict[str, Any], *, actor: str = "") -> dict[str, Any]:
    """Insert a new HQ ICMAS row. Operator supplies the BCODE (manual numbering)."""
    settings = get_hq_receive_settings()
    if not settings.write_enabled:
        raise HqReceiveError(
            "write_disabled",
            "ยังไม่เปิด HQ_RECEIVE_PIMAS_WRITE_ENABLED จึงยังไม่สร้างรหัสสินค้า",
        )

    bcode = str(payload.get("bcode") or "").strip().upper()
    descr = str(payload.get("descr") or "").strip()
    ui = str(payload.get("ui") or payload.get("ui1") or "ชิ้น").strip() or "ชิ้น"
    vendor = str(payload.get("vendor") or payload.get("vendor_acctno") or "").strip().upper()
    brand = str(payload.get("brand") or "").strip()
    model = str(payload.get("model") or "").strip()
    pcode = str(payload.get("pcode") or "").strip()
    mcode = str(payload.get("mcode") or "").strip()
    cost = float(payload.get("cost") or payload.get("costlast") or 0)
    qtymin = float(payload.get("qtymin") or 0)

    if not bcode:
        raise HqReceiveError("missing_bcode", "กรอกรหัสสินค้า")
    if len(bcode) > 20:
        raise HqReceiveError("bcode_too_long", "รหัสสินค้ายาวเกิน 20 ตัวอักษร")
    if not descr:
        raise HqReceiveError("missing_descr", "กรอกชื่อสินค้า")
    if len(descr) > 60:
        descr = descr[:60]

    main = payload.get("main")
    if main is None or main == "":
        main = _main_from_bcode(bcode)
    else:
        try:
            main = int(main)
        except (TypeError, ValueError) as exc:
            raise HqReceiveError("bad_main", "หมวด MAIN ไม่ถูกต้อง") from exc

    engine = writer_engine_for_branch("hq")
    try:
        with engine.begin() as conn:
            exists = conn.execute(
                text(
                    """
                    SELECT TOP 1 LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE
                    FROM dbo.ICMAS WITH (UPDLOCK, HOLDLOCK)
                    WHERE LTRIM(RTRIM(BCODE)) = :bcode
                    """
                ),
                {"bcode": bcode},
            ).mappings().first()
            if exists:
                raise HqReceiveError("bcode_exists", f"รหัส {bcode} มีในระบบแล้ว")

            conn.execute(
                text(
                    """
                    INSERT INTO dbo.ICMAS (
                      BCODE, DESCR, UI1, VENDOR, BRAND, MODEL, PCODE, MCODE,
                      MAIN, COSTLAST, COSTNET, PRICE1,
                      QTYOH2, QTYOH1, QTYBEG2, QTYBEG1, QTYMIN, QTYGET, QTYMAX,
                      MTP2, STATUS, CANCELED, ISVAT, SERIAL, MIX, EXMPT
                    ) VALUES (
                      :bcode, :descr, :ui1, :vendor, :brand, :model, :pcode, :mcode,
                      :main, :costlast, :costnet, :price1,
                      0, 0, 0, 0, :qtymin, 0, 0,
                      0, 1, 'N', 'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "bcode": bcode,
                    "descr": descr,
                    "ui1": ui[:10],
                    "vendor": (vendor or None) and vendor[:10],
                    "brand": (brand or None) and brand[:25],
                    "model": (model or None) and model[:25],
                    "pcode": (pcode or None) and pcode[:15],
                    "mcode": (mcode or None) and mcode[:15],
                    "main": main,
                    "costlast": cost if cost > 0 else None,
                    "costnet": cost if cost > 0 else None,
                    "price1": None,
                    "qtymin": qtymin,
                },
            )
    except HqReceiveError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="ICMAS")
        if hint:
            raise HqReceiveError(
                "permission_denied",
                hint + " — ต้อง GRANT INSERT ON dbo.ICMAS ให้ python_writer",
            ) from exc
        raise HqReceiveError("sql_error", str(exc)) from exc

    return {
        "bcode": bcode,
        "descr": descr,
        "ui": ui[:10],
        "vendor": vendor,
        "brand": brand,
        "model": model,
        "pcode": pcode,
        "mcode": mcode,
        "cost": cost,
        "costlast": cost,
        "main": main,
        "created_by": (actor or "")[:80],
    }
