"""Write helpers for PARTS9 Explorer product edit / waiting / images.

All ICMAS/ICLOW writes target HQ (KSS). Reuses hq-receive create/update,
hq-po QTYMIN, transfer ICLOW insert, and LINE image storage helpers.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from src.hq_po.config import get_hq_po_settings
from src.hq_po.guards import HqPoError
from src.hq_po.service import update_product_qtymin
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.icmas_create import create_product, update_product
from src.transfer.writers._engine import (
    transfer_write_permission_hint,
    writer_engine_for_branch,
)
from src.transfer.writers.iclow_low import (
    force_insert_waiting_iclow,
    open_iclow_id,
)


class ExplorerWriteError(Exception):
    def __init__(self, code: str, message: str, *, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


_NOT_CANCELED = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'"
_NOT_RECEIVED = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) <> 'Y'"
_ORDERED_N = "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) <> 'Y'"


def _require_stamp(*, action: str) -> None:
    settings = get_hq_po_settings()
    if not settings.stamp_enabled:
        raise ExplorerWriteError(
            "stamp_disabled",
            f"ยังไม่เปิด HQ_PO_ICLOW_STAMP_ENABLED จึงยังไม่{action}",
        )


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _engine():
    return writer_engine_for_branch("hq")


def create_product_from_explorer(payload: dict[str, Any], *, actor: str = "") -> dict[str, Any]:
    try:
        return create_product(payload, actor=actor)
    except HqReceiveError as exc:
        raise ExplorerWriteError(exc.code, str(exc)) from exc


def update_product_from_explorer(
    bcode: str, payload: dict[str, Any], *, actor: str = ""
) -> dict[str, Any]:
    try:
        return update_product(bcode, payload, actor=actor)
    except HqReceiveError as exc:
        raise ExplorerWriteError(exc.code, str(exc)) from exc


def update_qtymin_from_explorer(bcode: str, qtymin: Any) -> dict[str, Any]:
    try:
        return update_product_qtymin(bcode, qtymin)
    except HqPoError as exc:
        raise ExplorerWriteError(exc.code, str(exc)) from exc


def update_qtyget(bcode: str, qtyget: Any) -> dict[str, Any]:
    """Set HQ ICMAS.QTYGET (standard order lot). Zero clears the lot."""
    _require_stamp(action="แก้ล็อตสั่งซื้อ")
    code = str(bcode or "").strip()
    if not code:
        raise ExplorerWriteError("missing_bcode", "ไม่มีรหัสสินค้า")
    value = _num(qtyget)
    if value is None or value != value:
        raise ExplorerWriteError("bad_qtyget", "ล็อตสั่งซื้อต้องเป็นตัวเลข")
    if value < 0:
        raise ExplorerWriteError("bad_qtyget", "ล็อตสั่งซื้อต้องไม่ติดลบ")
    try:
        with _engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE dbo.ICMAS
                    SET QTYGET = :qtyget
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                    """
                ),
                {"bcode": code, "qtyget": value},
            )
            if result.rowcount < 1:
                raise ExplorerWriteError("missing", f"ไม่พบ {code} ใน ICMAS")
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1 QTYGET, QTYMIN, QTYOH2
                    FROM dbo.ICMAS
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                    """
                ),
                {"bcode": code},
            ).mappings().first()
    except ExplorerWriteError:
        raise
    except Exception as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="ICMAS")
        if hint:
            raise ExplorerWriteError("permission_denied", hint) from exc
        raise ExplorerWriteError("icmas_update_failed", str(exc)) from exc
    return {
        "bcode": code,
        "qtyget": value,
        "qtymin": _num(row.get("QTYMIN")) if row else None,
        "qtyoh2": _num(row.get("QTYOH2")) if row else None,
    }


def _default_waiting_qty(*, qtyget: Any, qtymin: Any, qtyoh: Any) -> float:
    lot = _num(qtyget) or 0.0
    if lot > 0:
        return lot
    minimum = _num(qtymin)
    on_hand = _num(qtyoh) or 0.0
    if minimum is not None and minimum > 0:
        gap = minimum - on_hand
        if gap > 0:
            return gap
    return 1.0


def lookup_open_waiting(bcode: str) -> dict[str, Any] | None:
    """Open รอสั่ง row only (ORDERED ≠ Y). ค้างรับ is ignored for edit UI."""
    code = str(bcode or "").strip()
    if not code:
        return None
    try:
        engine = _engine()
    except Exception:
        from src.parts9_explorer.db import get_site_engine

        engine = get_site_engine("hq")
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT TOP 1
                      CONVERT(bigint, ID) AS ID,
                      QTY
                    FROM dbo.ICLOW
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                      AND {_NOT_CANCELED}
                      AND {_NOT_RECEIVED}
                      AND {_ORDERED_N}
                    ORDER BY ID DESC
                    """
                ),
                {"bcode": code},
            ).mappings().first()
    except Exception:
        return None
    if not row:
        return None
    return {"iclow_id": int(row["ID"]), "qty": _num(row.get("QTY")) or 0.0}


def put_in_waiting(bcode: str, *, qty: Any = None) -> dict[str, Any]:
    """Force-insert an HQ ICLOW รอสั่ง row (ORDERED='N')."""
    _require_stamp(action="ใส่รอสั่งซื้อ")
    code = str(bcode or "").strip()
    if not code:
        raise ExplorerWriteError("missing_bcode", "ไม่มีรหัสสินค้า")
    try:
        with _engine().begin() as conn:
            existing = open_iclow_id(conn, code)
            if existing is not None:
                waiting = None
                row = conn.execute(
                    text(
                        f"""
                        SELECT TOP 1 CONVERT(bigint, ID) AS ID, QTY,
                          LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) AS ORDERED
                        FROM dbo.ICLOW
                        WHERE ID = :id
                        """
                    ),
                    {"id": existing},
                ).mappings().first()
                if row:
                    waiting = {
                        "iclow_id": int(row["ID"]),
                        "qty": _num(row.get("QTY")) or 0.0,
                        "ordered": str(row.get("ORDERED") or "").strip().upper(),
                    }
                raise ExplorerWriteError(
                    "already_open",
                    f"{code} มีแถว ICLOW ค้างอยู่แล้ว (#{existing})",
                    extra={"iclow_id": existing, "waiting": waiting},
                )
            product = conn.execute(
                text(
                    """
                    SELECT TOP 1
                      QTYGET, QTYMIN, QTYOH2
                    FROM dbo.ICMAS
                    WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) = :bcode
                    """
                ),
                {"bcode": code},
            ).mappings().first()
            if not product:
                raise ExplorerWriteError("missing", f"ไม่พบ {code} ใน ICMAS")
            asked = _num(qty)
            if asked is not None and asked > 0:
                order_qty = asked
            else:
                order_qty = _default_waiting_qty(
                    qtyget=product.get("QTYGET"),
                    qtymin=product.get("QTYMIN"),
                    qtyoh=product.get("QTYOH2"),
                )
            if order_qty <= 0:
                raise ExplorerWriteError("bad_qty", "จำนวนสั่งต้องมากกว่า 0")
            qtyoh = _num(product.get("QTYOH2")) or 0.0
            iclow_id = force_insert_waiting_iclow(
                conn, bcode=code, qty=order_qty, qtyoh=qtyoh, on=date.today()
            )
            if not iclow_id:
                raise ExplorerWriteError("insert_failed", f"ใส่รอสั่ง {code} ไม่สำเร็จ")
    except ExplorerWriteError:
        raise
    except Exception as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="ICLOW")
        if hint:
            raise ExplorerWriteError("permission_denied", hint) from exc
        raise ExplorerWriteError("iclow_insert_failed", str(exc)) from exc
    return {"bcode": code, "iclow_id": iclow_id, "qty": order_qty}


def update_waiting_qty(iclow_id: int, qty: Any) -> dict[str, Any]:
    """Update QTY on a รอสั่ง ICLOW row only."""
    _require_stamp(action="แก้จำนวนรอสั่ง")
    try:
        row_id = int(iclow_id)
    except (TypeError, ValueError) as exc:
        raise ExplorerWriteError("missing", "ไม่มี ICLOW id") from exc
    value = _num(qty)
    if value is None or value != value or value <= 0:
        raise ExplorerWriteError("bad_qty", "จำนวนสั่งต้องมากกว่า 0")
    try:
        with _engine().begin() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT TOP 1
                      CONVERT(bigint, ID) AS ID,
                      LTRIM(RTRIM(CONVERT(nvarchar(40), BCODE))) AS BCODE,
                      QTY, PRICE,
                      LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(ORDERED,'')))) AS ORDERED,
                      LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(RECEIVED,'')))) AS RECEIVED,
                      LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) AS CANCELED
                    FROM dbo.ICLOW
                    WHERE ID = :id
                    """
                ),
                {"id": row_id},
            ).mappings().first()
            if not row:
                raise ExplorerWriteError("missing", f"ไม่พบ ICLOW {row_id}")
            if str(row.get("CANCELED") or "").strip().upper() == "Y":
                raise ExplorerWriteError("canceled", "แถวนี้ถูกยกเลิกแล้ว")
            if str(row.get("RECEIVED") or "").strip().upper() == "Y":
                raise ExplorerWriteError("already_received", "แถวนี้รับแล้ว")
            if str(row.get("ORDERED") or "").strip().upper() == "Y":
                raise ExplorerWriteError("already_ordered", "แถวนี้สั่งแล้ว — แก้จำนวนที่หน้า hq-po")
            price = _num(row.get("PRICE"))
            amount = (price * value) if price is not None else None
            result = conn.execute(
                text(
                    f"""
                    UPDATE dbo.ICLOW
                    SET QTY = :qty, AMOUNT = :amount
                    WHERE ID = :id
                      AND {_NOT_CANCELED}
                      AND {_NOT_RECEIVED}
                      AND {_ORDERED_N}
                    """
                ),
                {"id": row_id, "qty": value, "amount": amount},
            )
            if result.rowcount < 1:
                raise ExplorerWriteError("update_failed", "อัปเดตจำนวนไม่สำเร็จ")
    except ExplorerWriteError:
        raise
    except Exception as exc:
        hint = transfer_write_permission_hint(exc, branch="hq", tables="ICLOW")
        if hint:
            raise ExplorerWriteError("permission_denied", hint) from exc
        raise ExplorerWriteError("iclow_update_failed", str(exc)) from exc
    return {
        "iclow_id": row_id,
        "bcode": str(row.get("BCODE") or "").strip(),
        "qty": value,
    }


def upload_product_image_bytes(
    bcode: str, image_bytes: bytes, *, content_type: str | None = None
) -> dict[str, Any]:
    from src.handlers.image import (
        MAX_PRODUCT_IMAGES,
        build_public_storage_url,
        list_product_images,
        upload_product_image,
        SUPABASE_IMAGE_BUCKET,
    )

    code = str(bcode or "").strip()
    if not code:
        raise ExplorerWriteError("missing_bcode", "ไม่มีรหัสสินค้า")
    if not image_bytes:
        raise ExplorerWriteError("empty_image", "ไม่มีไฟล์รูป")
    try:
        result = upload_product_image(code, image_bytes, content_type=content_type)
    except ValueError as exc:
        raise ExplorerWriteError("image_error", str(exc)) from exc
    except Exception as exc:
        raise ExplorerWriteError("upload_failed", f"อัปโหลดรูปไม่สำเร็จ: {exc}") from exc
    paths = list_product_images(code, max_images=MAX_PRODUCT_IMAGES)
    photos = [
        build_public_storage_url(SUPABASE_IMAGE_BUCKET, path, version=str(int(date.today().toordinal())))
        for path in paths
    ]
    return {**result, "photos": photos, "paths": paths}


def delete_product_image(bcode: str, *, path: str | None = None, slot: int | None = None) -> dict[str, Any]:
    from src.handlers.image import (
        MAX_PRODUCT_IMAGES,
        SUPABASE_IMAGE_BUCKET,
        build_public_storage_url,
        expected_product_image_paths,
        list_product_images,
        supabase,
    )

    code = str(bcode or "").strip()
    if not code:
        raise ExplorerWriteError("missing_bcode", "ไม่มีรหัสสินค้า")
    target = (path or "").strip()
    if not target and slot is not None:
        try:
            slot_n = int(slot)
        except (TypeError, ValueError) as exc:
            raise ExplorerWriteError("bad_slot", "ช่องรูปไม่ถูกต้อง") from exc
        expected = expected_product_image_paths(code)
        if slot_n < 1 or slot_n > len(expected):
            raise ExplorerWriteError("bad_slot", "ช่องรูปไม่ถูกต้อง")
        target = expected[slot_n - 1]
    if not target:
        raise ExplorerWriteError("missing_path", "ระบุ path หรือ slot ของรูป")
    # Safety: only delete under this product folder.
    expected_set = set(expected_product_image_paths(code))
    if target not in expected_set:
        raise ExplorerWriteError("bad_path", "path รูปไม่ตรงกับรหัสสินค้านี้")
    try:
        supabase.storage.from_(SUPABASE_IMAGE_BUCKET).remove([target])
    except Exception as exc:
        raise ExplorerWriteError("delete_failed", f"ลบรูปไม่สำเร็จ: {exc}") from exc
    paths = list_product_images(code, max_images=MAX_PRODUCT_IMAGES)
    photos = [
        build_public_storage_url(SUPABASE_IMAGE_BUCKET, p, version=str(int(date.today().toordinal())))
        for p in paths
    ]
    return {"bcode": code, "deleted": target, "photos": photos, "paths": paths}
