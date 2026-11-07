"""Photos of goods just prepared, kept as evidence on the transfer bill."""

from __future__ import annotations

MAX_PREPARE_PHOTOS = 8
MAX_PREPARE_PHOTO_BYTES = 8 * 1024 * 1024


class PreparePhotoError(ValueError):
    pass


def image_suffix(data: bytes) -> str:
    """File suffix from the image bytes. Anything else is refused."""
    if len(data) < 12:
        raise PreparePhotoError("ไฟล์รูปว่างหรืออ่านไม่ได้")
    if len(data) > MAX_PREPARE_PHOTO_BYTES:
        raise PreparePhotoError("รูปใหญ่เกิน 8 MB")
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise PreparePhotoError("รองรับเฉพาะรูป jpg, png, webp")


def prepare_photo_path(transfer_id: str, photo_id: str, suffix: str) -> str:
    return f"public/transfer/{transfer_id}/{photo_id}{suffix}"


def photo_ids_to_link(
    rows: list[dict],
    *,
    transfer_id: str,
    shipment_id: str,
    photo_ids: list[str],
) -> list[str]:
    """Ids that may be attached to this shipment. Raises when one cannot."""
    wanted: list[str] = []
    seen: set[str] = set()
    for raw in photo_ids:
        photo_id = str(raw or "").strip()
        if not photo_id or photo_id in seen:
            continue
        seen.add(photo_id)
        wanted.append(photo_id)
    if len(wanted) > MAX_PREPARE_PHOTOS:
        raise PreparePhotoError(f"แนบได้ไม่เกิน {MAX_PREPARE_PHOTOS} รูป")
    by_id = {str(row.get("photo_id") or ""): row for row in rows}
    target = str(shipment_id or "")
    for photo_id in wanted:
        row = by_id.get(photo_id)
        if not row or str(row.get("transfer_id") or "") != transfer_id:
            raise PreparePhotoError("ไม่พบรูปหลักฐานของคำขอนี้")
        linked = str(row.get("shipment_id") or "")
        if linked and linked != target:
            raise PreparePhotoError("รูปนี้ถูกแนบกับใบโอนอื่นแล้ว")
    return wanted


def shipment_photo_count(rows: list[dict], *, shipment_id: str) -> int:
    target = str(shipment_id or "")
    if not target:
        return 0
    return sum(1 for row in rows if str(row.get("shipment_id") or "") == target)


def remaining_photo_slots(rows: list[dict], *, shipment_id: str) -> int:
    return max(0, MAX_PREPARE_PHOTOS - shipment_photo_count(rows, shipment_id=shipment_id))
