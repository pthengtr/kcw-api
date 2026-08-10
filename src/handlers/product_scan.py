"""Product scan via LINE camera / camera-roll photo (no LIFF).

Flow:
1. User sends สแกน / สแกนสินค้า / scan …
2. Bot replies with camera + cameraRoll quick replies and opens a short session
3. User sends a photo → kcw-api downloads it, decodes barcode, runs product search
4. Bot replies with the same product-search answer as typing the barcode directly
"""

from __future__ import annotations

import os
import time

from src.barcode import (
    BarcodeDecodeUnavailable,
    decode_barcodes_from_image,
    pick_best_barcode,
    sanitize_barcode,
)
from src.bot.line_bot import download_line_message_content
from src.handlers.product import handle_product_query_response

PRODUCT_SCAN_SESSION_TTL_SECONDS = int(
    os.getenv("PRODUCT_SCAN_SESSION_TTL_SECONDS", "600").strip() or "600"
)

# Compact command aliases (whitespace stripped, lowercased for Latin).
PRODUCT_SCAN_COMMANDS = {
    "สแกน",
    "สแกนสินค้า",
    "สแกนบาร์โค้ด",
    "สแกนบาร์โคด",
    "scan",
    "scanproduct",
    "scanbarcode",
    "scan product",
    "scan barcode",
}

# Legacy LIFF callback prefixes (still accepted if an old client posts text).
_CALLBACK_PREFIXES = (
    "📦 สแกนสินค้า:",
    "สแกนสินค้า:",
)

END_SESSION_WORDS = {
    "เสร็จ",
    "จบ",
    "done",
    "ยกเลิก",
    "cancel",
}

CONTINUE_SESSION_WORDS = {
    "สแกนต่อ",
    "ต่อ",
    "continue",
    "scan again",
    "scanagain",
}

PRODUCT_SCAN_SESSIONS: dict[str, dict] = {}


def _now() -> float:
    return time.time()


def _is_expired(session: dict | None) -> bool:
    if not session:
        return True
    return float(session.get("expires_at") or 0) < _now()


def _get_active_session(line_user_id: str | None) -> dict | None:
    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return None

    session = PRODUCT_SCAN_SESSIONS.get(line_user_id)
    if _is_expired(session):
        PRODUCT_SCAN_SESSIONS.pop(line_user_id, None)
        return None

    return session


def clear_product_scan_session(line_user_id: str | None):
    line_user_id = (line_user_id or "").strip()
    if line_user_id:
        PRODUCT_SCAN_SESSIONS.pop(line_user_id, None)


def _extend_session(session: dict):
    session["expires_at"] = _now() + PRODUCT_SCAN_SESSION_TTL_SECONDS


def _start_session(line_user_id: str):
    # Avoid fighting product-image upload/delete sessions for the next photo.
    try:
        from src.handlers import image as image_handler

        image_handler._clear_session(image_handler.UPLOAD_SESSIONS, line_user_id)
        image_handler._clear_session(image_handler.DELETE_SESSIONS, line_user_id)
    except Exception as e:
        print("PRODUCT SCAN CLEAR IMAGE SESSION ERROR:", e)

    PRODUCT_SCAN_SESSIONS[line_user_id] = {
        "expires_at": _now() + PRODUCT_SCAN_SESSION_TTL_SECONDS,
    }


def has_active_product_scan_session(line_user_id: str | None) -> bool:
    return _get_active_session(line_user_id) is not None


def _match_callback_prefix(text: str | None) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    for prefix in _CALLBACK_PREFIXES:
        if t.startswith(prefix):
            return prefix
    return None


def is_product_scan_callback(text: str | None) -> bool:
    """True when the message uses the legacy LIFF scan-callback prefix."""
    return _match_callback_prefix(text) is not None


def parse_product_scan_callback(text: str | None) -> str | None:
    """Extract a sanitized barcode from a legacy LIFF callback text."""
    prefix = _match_callback_prefix(text)
    if prefix is None:
        return None
    return sanitize_barcode((text or "").strip()[len(prefix) :])


def is_product_scan_command(text: str | None) -> bool:
    """True when the user is asking to open the product barcode scanner."""
    t = (text or "").strip()
    if not t:
        return False

    if is_product_scan_callback(t):
        return False

    compact = "".join(t.lower().split())
    aliases = {"".join(a.lower().split()) for a in PRODUCT_SCAN_COMMANDS}
    return compact in aliases


def _qr_message(label: str, text: str) -> dict:
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label,
            "text": text,
        },
    }


def _qr_camera(label: str = "ถ่ายรูป") -> dict:
    return {
        "type": "action",
        "action": {
            "type": "camera",
            "label": label,
        },
    }


def _qr_camera_roll(label: str = "เลือกรูป") -> dict:
    return {
        "type": "action",
        "action": {
            "type": "cameraRoll",
            "label": label,
        },
    }


def _build_session_quick_reply() -> dict:
    return {
        "items": [
            _qr_camera("ถ่ายบาร์โค้ด"),
            _qr_camera_roll("เลือกรูป"),
            _qr_message("ยกเลิก", "ยกเลิก"),
        ]
    }


def _build_after_scan_quick_reply(bcode: str) -> dict:
    items = [
        _qr_message("สแกนต่อ", "สแกนต่อ"),
        _qr_camera("ถ่ายบาร์โค้ด"),
        _qr_camera_roll("เลือกรูป"),
        _qr_message("เช็คสินค้า", f"เช็ค {bcode}"),
        _qr_message("จบ", "จบ"),
    ]
    return {"items": items}


def handle_product_scan_command(line_user_id: str | None = None) -> dict:
    """Start camera/photo barcode scan session (Reply API + quick replies)."""
    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return {
            "type": "text",
            "text": "ไม่พบ LINE user id จึงเริ่มโหมดสแกนสินค้าไม่ได้ครับ",
        }

    _start_session(line_user_id)

    return {
        "type": "text",
        "text": (
            "ส่งรูปบาร์โค้ดสินค้าได้เลยครับ\n"
            "กดถ่ายบาร์โค้ด หรือเลือกรูปจากอัลบั้ม\n"
            "ระบบจะอ่านรหัสแล้วค้นหาสินค้าให้อัตโนมัติ\n"
            'กด "ยกเลิก" เพื่อออกจากโหมดนี้'
        ),
        "quickReply": _build_session_quick_reply(),
    }


def handle_product_scan_session_text(line_user_id: str | None, text: str) -> dict | None:
    """Intercept text while the user is in product-scan mode. None if idle."""
    session = _get_active_session(line_user_id)
    if not session:
        return None

    t = (text or "").strip()
    t_lower = t.lower()
    compact = "".join(t_lower.split())

    if t_lower in END_SESSION_WORDS or compact in END_SESSION_WORDS:
        clear_product_scan_session(line_user_id)
        return {
            "type": "text",
            "text": "จบโหมดสแกนสินค้าแล้วครับ",
        }

    if t_lower in CONTINUE_SESSION_WORDS or compact in CONTINUE_SESSION_WORDS:
        session.pop("awaiting_continue", None)
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "ส่งรูปบาร์โค้ดถัดไปได้เลยครับ\n"
                'หรือกด "จบ" เพื่อออกจากโหมดสแกน'
            ),
            "quickReply": _build_session_quick_reply(),
        }

    # Legacy LIFF text callback while a session is open — treat as barcode.
    if is_product_scan_callback(t):
        return None

    # Allow follow-up product actions from after-scan quick replies to escape
    # scan mode (e.g. เช็ค {bcode}, รูป {bcode}).
    from src.handlers.check import is_check_request
    from src.handlers.image import is_image_command
    from src.handlers.product_snapshot import is_product_snapshot_request

    if is_check_request(t) or is_product_snapshot_request(t) or is_image_command(t):
        clear_product_scan_session(line_user_id)
        return None

    _extend_session(session)
    return {
        "type": "text",
        "text": (
            "ตอนนี้อยู่ในโหมดสแกนสินค้าครับ\n"
            "กรุณาส่งรูปบาร์โค้ด หรือพิมพ์ ยกเลิก เพื่อออก"
        ),
        "quickReply": _build_session_quick_reply(),
    }


def _lookup_barcode(engine, barcode: str, access: dict | None = None) -> dict:
    """Reuse the fast product-search path (same as typing the barcode)."""
    return handle_product_query_response(engine, barcode, access=access)


def _attach_after_scan_quick_reply(response: dict, barcode: str) -> dict:
    """Keep scan session usable: attach camera / สแกนต่อ on the reply."""
    qr = _build_after_scan_quick_reply(barcode)

    if response.get("type") == "messages":
        messages = response.get("messages") or []
        if messages:
            messages[-1] = dict(messages[-1])
            messages[-1]["quickReply"] = qr
            response = {**response, "messages": messages}
        return response

    response = dict(response)
    response["quickReply"] = qr
    return response


def handle_product_scan_callback(
    engine,
    user_text: str,
    access: dict | None = None,
    line_user_id: str | None = None,
) -> dict:
    """Back-compat for legacy LIFF callback text → product search."""
    barcode = parse_product_scan_callback(user_text)
    if not barcode:
        return {
            "type": "text",
            "text": (
                "อ่านรหัสจากข้อความสแกนไม่สำเร็จครับ\n"
                "กรุณาพิมพ์ สแกน แล้วส่งรูปบาร์โค้ดแทน"
            ),
        }

    if line_user_id:
        session = _get_active_session(line_user_id)
        if session is None:
            _start_session(line_user_id)
            session = _get_active_session(line_user_id)
        if session is not None:
            session["awaiting_continue"] = True
            _extend_session(session)

    response = _lookup_barcode(engine, barcode, access=access)
    return _attach_after_scan_quick_reply(response, barcode)


def handle_product_scan_image(
    engine,
    line_user_id: str | None,
    message_id: str | None,
    access: dict | None = None,
) -> dict | None:
    """
    Handle an inbound LINE image while a product-scan session is active.

    Returns None when there is no active product-scan session.
    """
    session = _get_active_session(line_user_id)
    if not session:
        return None

    line_user_id = (line_user_id or "").strip()
    session.pop("awaiting_continue", None)

    try:
        image_bytes, _content_type = download_line_message_content(message_id or "")
        raw_codes = decode_barcodes_from_image(image_bytes)
        barcode = pick_best_barcode(raw_codes)
    except BarcodeDecodeUnavailable as e:
        print("PRODUCT SCAN DECODER UNAVAILABLE:", e)
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "ระบบอ่านบาร์โค้ดยังไม่พร้อมใช้งานชั่วคราวครับ\n"
                "กรุณาพิมพ์รหัสสินค้าแทน หรือลองใหม่ภายหลัง\n"
                'หรือพิมพ์ "ยกเลิก" เพื่อออก'
            ),
            "quickReply": _build_session_quick_reply(),
        }
    except Exception as e:
        print("PRODUCT SCAN IMAGE ERROR:", e)
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "อ่านบาร์โค้ดจากรูปไม่สำเร็จครับ กรุณาส่งรูปใหม่อีกครั้ง\n"
                'หรือพิมพ์ "ยกเลิก" เพื่อออก'
            ),
            "quickReply": _build_session_quick_reply(),
        }

    if not barcode:
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "ไม่พบบาร์โค้ดในรูปนี้ครับ\n"
                "ลองถ่ายใกล้ขึ้น ให้รหัสคมชัด หรือเลือกไฟล์รูปอื่น\n"
                'หรือพิมพ์ "ยกเลิก" เพื่อออก'
            ),
            "quickReply": _build_session_quick_reply(),
        }

    session["awaiting_continue"] = True
    session["last_barcode"] = barcode
    _extend_session(session)

    response = _lookup_barcode(engine, barcode, access=access)
    # Soft-prefix decoded code so the shop staff sees what was read.
    if response.get("type") == "text" and response.get("text"):
        response = dict(response)
        response["text"] = f"อ่านรหัส: {barcode}\n\n{response['text']}"

    return _attach_after_scan_quick_reply(response, barcode)
