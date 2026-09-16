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
    needs_catalog_confirm: bool = False


GetByBcodeFn = Callable[[str], dict[str, Any] | None]
ShipFromMetaFn = Callable[[str], dict[str, Any] | None]
CreateGroupFn = Callable[..., dict[str, Any]]
AddMemberFn = Callable[..., Any]

# Operator-facing code returned when ส่งแทน needs an explicit catalog add.
NEEDS_CATALOG_CONFIRM = "needs_catalog_confirm"


def is_catalog_gap_error(error: str | None) -> bool:
    """True when resolve failed only because peer is not in the same catalog group."""
    if not error:
        return False
    if "รายการขออื่น" in error or "clash" in error.lower():
        return False
    if "ไม่พบ" in error and "ICMAS" in error:
        return False
    return "กลุ่ม" in error


def ensure_catalog_pair(
    *,
    request_bcode: str,
    ship_as_bcode: str,
    get_by_bcode: GetByBcodeFn,
    create_group: CreateGroupFn,
    add_member: AddMemberFn,
    created_by: str | None = None,
    note: str = "from transfer ส่งแทน",
) -> dict[str, Any]:
    """Link request + peer in catalog (create group or add member).

    Same rules as Explorer promote: one group per BCODE; cannot merge two groups.
    """
    requested = (request_bcode or "").strip()
    alt = (ship_as_bcode or "").strip()
    if not requested or not alt:
        raise ValueError("request_bcode and ship_as_bcode required")
    if requested == alt:
        group = get_by_bcode(requested)
        return group or {}

    req_group = get_by_bcode(requested)
    alt_group = get_by_bcode(alt)
    req_gid = (req_group or {}).get("group_id")
    alt_gid = (alt_group or {}).get("group_id")

    if req_gid and alt_gid:
        if req_gid == alt_gid:
            return req_group or {}
        raise ValueError(
            f"ส่งแทนไม่ได้ — {requested} กับ {alt} อยู่คนละกลุ่มทดแทน "
            f"(ต้องจัดการใน Explorer)"
        )

    if req_gid and not alt_gid:
        add_member(str(req_gid), alt, note=note)
        return get_by_bcode(requested) or req_group or {}

    if alt_gid and not req_gid:
        add_member(str(alt_gid), requested, note=note)
        return get_by_bcode(alt) or alt_group or {}

    return create_group(
        name=None,
        note=note,
        created_by=created_by,
        members=[{"bcode": requested}, {"bcode": alt}],
    )


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
            needs_catalog_confirm=True,
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
            needs_catalog_confirm=True,
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
