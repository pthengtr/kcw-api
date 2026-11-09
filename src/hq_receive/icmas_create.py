"""Create / update HQ ICMAS product rows from the receive screen."""

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


def _clip(value: Any, n: int) -> str | None:
    text_value = str(value or "").strip()
    if not text_value:
        return None
    return text_value[:n]


def _require_write(*, action: str = "บันทึกรหัสสินค้า") -> None:
    settings = get_hq_receive_settings()
    if not settings.write_enabled:
        raise HqReceiveError(
            "write_disabled",
            f"ยังไม่เปิด HQ_RECEIVE_PIMAS_WRITE_ENABLED จึงยังไม่{action}",
        )


def _parse_money(raw: Any) -> float:
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def create_product(payload: dict[str, Any], *, actor: str = "") -> dict[str, Any]:
    """Insert a new HQ ICMAS row. Operator supplies the BCODE (manual numbering)."""
    _require_write(action="สร้างรหัสสินค้า")

    bcode = str(payload.get("bcode") or "").strip().upper()
    descr = str(payload.get("descr") or "").strip()
    ui = str(payload.get("ui") or payload.get("ui1") or "ชิ้น").strip() or "ชิ้น"
    vendor = str(payload.get("vendor") or payload.get("vendor_acctno") or "").strip().upper()
    brand = str(payload.get("brand") or "").strip()
    model = str(payload.get("model") or "").strip()
    pcode = str(payload.get("pcode") or "").strip()
    mcode = str(payload.get("mcode") or "").strip()
    location1 = str(payload.get("location1") or payload.get("location") or "").strip()
    code1 = str(payload.get("code1") or "").strip().upper()
    cost = _parse_money(payload.get("cost") or payload.get("costlast") or payload.get("ค่า"))
    price1 = _parse_money(payload.get("price1") or payload.get("price") or payload.get("ราคา"))
    qtymin = _parse_money(payload.get("qtymin") or 0)

    if not bcode:
        raise HqReceiveError("missing_bcode", "กรอกรหัสสินค้า")
    if len(bcode) > 20:
        raise HqReceiveError("bcode_too_long", "รหัสสินค้ายาวเกิน 20 ตัวอักษร")
    if not descr:
        raise HqReceiveError("missing_descr", "กรอกชื่อสินค้า")
    if len(descr) > 60:
        descr = descr[:60]
    if code1 and len(code1) > 1:
        # CODE1 is a single-letter control code (I/C/O/…).
        code1 = code1[:1]

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
                      LOCATION1, CODE1, MAIN, COSTLAST, COSTNET, PRICE1,
                      QTYOH2, QTYOH1, QTYBEG2, QTYBEG1, QTYMIN, QTYGET, QTYMAX,
                      MTP2, STATUS, CANCELED, ISVAT, SERIAL, MIX, EXMPT
                    ) VALUES (
                      :bcode, :descr, :ui1, :vendor, :brand, :model, :pcode, :mcode,
                      :location1, :code1, :main, :costlast, :costnet, :price1,
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
                    "brand": _clip(brand, 25),
                    "model": _clip(model, 25),
                    "pcode": _clip(pcode, 15),
                    "mcode": _clip(mcode, 15),
                    "location1": _clip(location1, 10),
                    "code1": _clip(code1, 1),
                    "main": main,
                    "costlast": cost if cost > 0 else None,
                    "costnet": cost if cost > 0 else None,
                    "price1": price1 if price1 > 0 else None,
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
        "location1": location1,
        "code1": code1,
        "cost": cost,
        "costlast": cost,
        "price1": price1,
        "main": main,
        "created_by": (actor or "")[:80],
    }


def update_product(bcode: str, payload: dict[str, Any], *, actor: str = "") -> dict[str, Any]:
    """Update identity fields on an existing HQ ICMAS row."""
    _require_write(action="แก้รหัสสินค้า")

    code = str(bcode or payload.get("bcode") or "").strip().upper()
    if not code:
        raise HqReceiveError("missing_bcode", "ไม่มีรหัสสินค้า")

    descr = payload.get("descr")
    brand = payload.get("brand")
    model = payload.get("model")
    pcode = payload.get("pcode")
    mcode = payload.get("mcode")
    location1 = payload.get("location1", payload.get("location"))
    code1 = payload.get("code1")
    price_raw = payload.get("price1", payload.get("price"))
    cost_raw = payload.get("cost", payload.get("costlast"))

    sets: list[str] = []
    params: dict[str, Any] = {"bcode": code}

    if descr is not None:
        text_descr = str(descr).strip()
        if not text_descr:
            raise HqReceiveError("missing_descr", "กรอกชื่อสินค้า")
        sets.append("DESCR = :descr")
        params["descr"] = text_descr[:60]
    if brand is not None:
        sets.append("BRAND = :brand")
        params["brand"] = _clip(brand, 25)
    if model is not None:
        sets.append("MODEL = :model")
        params["model"] = _clip(model, 25)
    if pcode is not None:
        sets.append("PCODE = :pcode")
        params["pcode"] = _clip(pcode, 15)
    if mcode is not None:
        sets.append("MCODE = :mcode")
        params["mcode"] = _clip(mcode, 15)
    if location1 is not None:
        sets.append("LOCATION1 = :location1")
        params["location1"] = _clip(location1, 10)
    if code1 is not None:
        c1 = str(code1 or "").strip().upper()[:1] or None
        sets.append("CODE1 = :code1")
        params["code1"] = c1
    if price_raw is not None and str(price_raw).strip() != "":
        price1 = _parse_money(price_raw)
        sets.append("PRICE1 = :price1")
        params["price1"] = price1 if price1 > 0 else None
    if cost_raw is not None and str(cost_raw).strip() != "":
        cost = _parse_money(cost_raw)
        sets.append("COSTLAST = :costlast")
        sets.append("COSTNET = :costnet")
        params["costlast"] = cost if cost > 0 else None
        params["costnet"] = cost if cost > 0 else None

    if not sets:
        raise HqReceiveError("nothing_to_update", "ไม่มีฟิลด์ที่ต้องการแก้")

    engine = writer_engine_for_branch("hq")
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    f"""
                    UPDATE dbo.ICMAS
                    SET {", ".join(sets)}
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                    """
                ),
                params,
            )
            if result.rowcount < 1:
                raise HqReceiveError("missing_icmas", f"ไม่พบรหัส {code} ใน ICMAS")
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1
                      LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
                      LTRIM(RTRIM(CONVERT(nvarchar(400), COALESCE(DESCR,'')))) AS DESCR,
                      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(BRAND,'')))) AS BRAND,
                      LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(MODEL,'')))) AS MODEL,
                      LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PCODE,'')))) AS PCODE,
                      LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MCODE,'')))) AS MCODE,
                      LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(LOCATION1,'')))) AS LOCATION1,
                      LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CODE1,'')))) AS CODE1,
                      PRICE1, COSTLAST, COSTNET,
                      LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(UI1,'')))) AS UI1
                    FROM dbo.ICMAS
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                    """
                ),
                {"bcode": code},
            ).mappings().first()
    except HqReceiveError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="ICMAS")
        if hint:
            raise HqReceiveError(
                "permission_denied",
                hint + " — ต้อง GRANT UPDATE ON dbo.ICMAS ให้ python_writer",
            ) from exc
        raise HqReceiveError("sql_error", str(exc)) from exc

    product = row or {}
    costlast = float(product.get("COSTLAST") or 0) or 0.0
    costnet = float(product.get("COSTNET") or 0) or 0.0
    return {
        "bcode": str(product.get("BCODE") or code).strip(),
        "descr": str(product.get("DESCR") or "").strip(),
        "brand": str(product.get("BRAND") or "").strip(),
        "model": str(product.get("MODEL") or "").strip(),
        "pcode": str(product.get("PCODE") or "").strip(),
        "mcode": str(product.get("MCODE") or "").strip(),
        "location1": str(product.get("LOCATION1") or "").strip(),
        "code1": str(product.get("CODE1") or "").strip(),
        "price1": product.get("PRICE1"),
        "cost": costlast if costlast > 0 else costnet,
        "costlast": costlast if costlast > 0 else None,
        "ui": str(product.get("UI1") or "").strip(),
        "updated_by": (actor or "")[:80],
    }
