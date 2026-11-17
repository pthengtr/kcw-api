"""Resolve printable staff names from ops.staff_profiles by LINE user id."""

from __future__ import annotations

from typing import Any

from src.db.engine import get_engine
from src.staff.errors import StaffMappingError

# Local / Tailscale sessions are not real LINE users.
SYSTEM_LINE_USER_IDS = frozenset({"lan", "tailscale", "unknown", ""})


def format_issuer_label(full_name: str, nickname: str = "") -> str:
    full = (full_name or "").strip()
    nick = (nickname or "").strip()
    if full and nick:
        return f"{full} ({nick})"
    return full or nick


def get_staff_profile(line_user_id: str) -> dict[str, Any] | None:
    uid = (line_user_id or "").strip()
    if not uid or uid in SYSTEM_LINE_USER_IDS:
        return None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.exec_driver_sql(
                """
                select line_user_id, full_name, nickname, is_active
                from ops.staff_profiles
                where line_user_id = %s
                """,
                (uid,),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "line_user_id": row[0],
        "full_name": row[1],
        "nickname": row[2],
        "is_active": bool(row[3]),
    }


def match_legacy_by_display_name(display_name: str) -> dict[str, str] | None:
    """Fallback match for old PARTS9 SALE strings (LINE display, truncated)."""
    from src.online_sale.staff import match_staff

    hit = match_staff(display_name)
    if not hit:
        return None
    return {"full_name": hit["full_name"], "nickname": hit["nick"]}


def issuer_label_for_actor(
    *,
    line_user_id: str = "",
    display_name: str = "",
) -> str:
    """Printable issuer label for a live actor (or legacy SALE string)."""
    profile = get_staff_profile(line_user_id)
    if profile and profile.get("is_active"):
        return format_issuer_label(profile["full_name"], profile["nickname"])

    hit = match_legacy_by_display_name(display_name)
    if hit:
        return format_issuer_label(hit["full_name"], hit["nickname"])

    return (display_name or line_user_id or "").strip()


def require_staff_mapping(line_user_id: str, display_name: str = "") -> dict[str, Any]:
    """Raise when a real LINE user has no active staff profile."""
    uid = (line_user_id or "").strip()
    if uid in SYSTEM_LINE_USER_IDS:
        return {"ok": True, "system": True}

    profile = get_staff_profile(uid)
    if profile and profile.get("is_active"):
        return {
            "ok": True,
            "line_user_id": uid,
            "full_name": profile["full_name"],
            "nickname": profile["nickname"],
            "issuer_label": format_issuer_label(
                profile["full_name"], profile["nickname"]
            ),
        }

    who = (display_name or uid or "ผู้ใช้นี้").strip()
    raise StaffMappingError(
        "staff_unmapped",
        f"ยังไม่ได้ตั้งชื่อจริงของ {who} ในระบบพนักงาน "
        f"— ติดต่อผู้ดูแลเพื่อเพิ่มรายชื่อก่อนออกเอกสาร "
        f"หรือยืนยันเพื่อใช้ชื่อ LINE ชั่วคราว",
        status=409,
    )
