"""Validate prepare ``ship_as_bcode`` (ส่งแทน) — Phase 3b."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ShipAsResult:
    ship_bcode: str
    requested_bcode: str
    is_substitute: bool
    descr: str | None = None
    error: str | None = None


GetByBcodeFn = Callable[[str], dict[str, Any] | None]
ShipFromMetaFn = Callable[[str], dict[str, Any] | None]


def resolve_ship_as(
    *,
    request_bcode: str,
    ship_as_bcode: str | None,
    other_request_bcodes: set[str],
    get_by_bcode: GetByBcodeFn,
    ship_from_meta: ShipFromMetaFn,
) -> ShipAsResult:
    """Resolve shipped BCODE for one prepare line.

    Clash rule (v1): reject if ``ship_as_bcode`` is already another request line's
    BCODE on the same transfer.
    """
    requested = (request_bcode or "").strip()
    if not requested:
        return ShipAsResult(
            ship_bcode="",
            requested_bcode="",
            is_substitute=False,
            error="ไม่ระบุรหัสคำขอ",
        )

    alt = (ship_as_bcode or "").strip()
    if not alt or alt == requested:
        return ShipAsResult(
            ship_bcode=requested,
            requested_bcode=requested,
            is_substitute=False,
        )

    if alt in other_request_bcodes:
        return ShipAsResult(
            ship_bcode=requested,
            requested_bcode=requested,
            is_substitute=False,
            error=(
                f"ส่งแทน {alt} ไม่ได้ — รหัสนี้เป็นรายการขออื่นในคำขอเดียวกัน "
                f"(clash กับ unique transfer line)"
            ),
        )

    group = get_by_bcode(requested)
    if not group:
        return ShipAsResult(
            ship_bcode=requested,
            requested_bcode=requested,
            is_substitute=False,
            error=f"ส่งแทนไม่ได้ — {requested} ไม่อยู่ในกลุ่มทดแทน",
        )
    members = {
        str(m.get("bcode") or "").strip()
        for m in (group.get("members") or [])
        if str(m.get("bcode") or "").strip()
    }
    if alt not in members:
        return ShipAsResult(
            ship_bcode=requested,
            requested_bcode=requested,
            is_substitute=False,
            error=f"ส่งแทนไม่ได้ — {alt} ไม่ได้อยู่กลุ่มเดียวกับ {requested}",
        )

    meta = ship_from_meta(alt)
    if not meta:
        return ShipAsResult(
            ship_bcode=requested,
            requested_bcode=requested,
            is_substitute=False,
            error=f"ส่งแทนไม่ได้ — ไม่พบ {alt} ใน ICMAS สาขาต้นทาง",
        )

    descr = (meta.get("descr") or "").strip() or None
    return ShipAsResult(
        ship_bcode=alt,
        requested_bcode=requested,
        is_substitute=True,
        descr=descr,
    )
