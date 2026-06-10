import os
import time

from src.ai.table_extractor import extract_table_from_image
from src.bot.line_bot import download_line_message_content
from src.printout.render import render_printout_html
from src.printout.enrich import enrich_printout_rows
from src.printout.store import PRINTOUT_TTL_SECONDS, get_printout, save_printout

TABLE_PRINTOUT_SESSION_TTL_SECONDS = int(
    os.getenv("TABLE_PRINTOUT_SESSION_TTL_SECONDS", "600").strip()
)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

TABLE_PRINTOUT_COMMANDS = {
    "สแกน",
    "สแกนตาราง",
    "printout",
    "พิมพ์ตาราง",
}

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
    "สแกน",
}

TABLE_PRINTOUT_SESSIONS: dict[str, dict] = {}


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

    session = TABLE_PRINTOUT_SESSIONS.get(line_user_id)
    if _is_expired(session):
        TABLE_PRINTOUT_SESSIONS.pop(line_user_id, None)
        return None

    return session


def _clear_session(line_user_id: str | None):
    line_user_id = (line_user_id or "").strip()
    if line_user_id:
        TABLE_PRINTOUT_SESSIONS.pop(line_user_id, None)


def _extend_session(session: dict):
    session["expires_at"] = _now() + TABLE_PRINTOUT_SESSION_TTL_SECONDS


def _start_session(line_user_id: str):
    TABLE_PRINTOUT_SESSIONS[line_user_id] = {
        "expires_at": _now() + TABLE_PRINTOUT_SESSION_TTL_SECONDS,
    }


def is_table_printout_command(text: str) -> bool:
    t = (text or "").strip().lower()
    compact = "".join(t.split())
    return compact in TABLE_PRINTOUT_COMMANDS


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
            _qr_camera_roll("เลือกรูป"),
            _qr_camera("ถ่ายรูป"),
            _qr_message("ยกเลิก", "ยกเลิก"),
        ]
    }


def _build_continue_quick_reply() -> dict:
    return {
        "items": [
            _qr_message("สแกนต่อ", "สแกนต่อ"),
            _qr_camera_roll("เลือกรูป"),
            _qr_camera("ถ่ายรูป"),
            _qr_message("จบ", "จบ"),
        ]
    }


def _build_printout_url(token: str) -> str:
    path = f"/printout/{token}"
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}{path}"
    return path


def _format_token_usage(extracted: dict) -> str | None:
    usage = extracted.get("usage") or {}
    total = int(usage.get("total_tokens") or 0)
    if not total:
        return None

    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return f"ใช้ token รวม: {total:,} (input {input_tokens:,} / output {output_tokens:,})"


def _ttl_hours_text() -> str:
    hours = PRINTOUT_TTL_SECONDS / 3600
    if hours >= 1 and float(int(hours)) == hours:
        return f"{int(hours)} ชม."
    return f"{PRINTOUT_TTL_SECONDS // 60} นาที"


def handle_table_printout_command(line_user_id: str | None) -> dict:
    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return {
            "type": "text",
            "text": "ไม่พบ LINE user id จึงเริ่มโหมดสแกนตารางไม่ได้ครับ",
        }

    _start_session(line_user_id)

    return {
        "type": "text",
        "text": (
            "ส่งรูปตารางได้เลยครับ\n"
            "ระบบจะสแกนข้อมูลแล้วสร้างหน้าเว็บสำหรับตรวจและพิมพ์\n"
            'กด "ยกเลิก" เพื่อออกจากโหมดนี้'
        ),
        "quickReply": _build_session_quick_reply(),
    }


def handle_table_printout_session_text(line_user_id: str | None, text: str) -> dict | None:
    session = _get_active_session(line_user_id)
    if not session:
        return None

    t = (text or "").strip()
    t_lower = t.lower()
    compact = "".join(t_lower.split())

    if t_lower in END_SESSION_WORDS or compact in END_SESSION_WORDS:
        _clear_session(line_user_id)
        return {
            "type": "text",
            "text": "จบโหมดสแกนตารางแล้วครับ",
        }

    if session.get("awaiting_continue"):
        if t_lower in CONTINUE_SESSION_WORDS or compact in CONTINUE_SESSION_WORDS:
            session.pop("awaiting_continue", None)
            _extend_session(session)
            return {
                "type": "text",
                "text": (
                    "ส่งรูปตารางถัดไปได้เลยครับ\n"
                    'หรือกด "จบ" เพื่อออกจากโหมดสแกน'
                ),
                "quickReply": _build_continue_quick_reply(),
            }

        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "ต้องการสแกนรูปถัดไปหรือจบครับ?\n"
                'กด "สแกนต่อ" หรือส่งรูปใหม่ได้เลย\n'
                'หรือกด "จบ" เพื่อออก'
            ),
            "quickReply": _build_continue_quick_reply(),
        }

    _extend_session(session)
    return {
        "type": "text",
        "text": (
            "ตอนนี้อยู่ในโหมดสแกนตารางครับ\n"
            "กรุณาส่งรูปตาราง หรือพิมพ์ ยกเลิก เพื่อออก"
        ),
        "quickReply": _build_session_quick_reply(),
    }


def has_active_table_printout_session(line_user_id: str | None) -> bool:
    return _get_active_session(line_user_id) is not None


def handle_table_printout_image(
    line_user_id: str | None,
    message_id: str | None,
    engine,
) -> dict | None:
    session = _get_active_session(line_user_id)
    if not session:
        return None

    line_user_id = (line_user_id or "").strip()
    session.pop("awaiting_continue", None)

    try:
        image_bytes, content_type = download_line_message_content(message_id or "")
        extracted = extract_table_from_image(image_bytes, content_type=content_type)
        if not extracted.get("error"):
            extracted = enrich_printout_rows(engine, extracted)
    except Exception as e:
        print("TABLE PRINTOUT ERROR:", e)
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "สแกนตารางไม่สำเร็จครับ กรุณาส่งรูปใหม่อีกครั้ง\n"
                'หรือพิมพ์ "ยกเลิก" เพื่อออก'
            ),
            "quickReply": _build_session_quick_reply(),
        }

    if extracted.get("error") == "no_table_detected":
        _extend_session(session)
        return {
            "type": "text",
            "text": (
                "ไม่พบตารางในรูปนี้ครับ\n"
                "ลองส่งรูปที่ชัดขึ้น หรือพิมพ์ ยกเลิก เพื่อออก"
            ),
            "quickReply": _build_session_quick_reply(),
        }

    token = save_printout(
        extracted,
        line_user_id=line_user_id,
        source="line",
    )

    session["awaiting_continue"] = True
    _extend_session(session)

    url = _build_printout_url(token)
    row_count = len(extracted.get("rows") or [])
    warning_count = len(extracted.get("warnings") or [])

    lines = [
        "สแกนตารางเสร็จแล้วครับ",
        f"พบ {row_count} แถว (เติมข้อมูลสินค้าจากรหัสสินค้าแล้ว)",
        f"เปิดลิงก์เพื่อตรวจและพิมพ์:\n{url}",
        f"ลิงก์หมดอายุใน {_ttl_hours_text()}",
    ]
    if warning_count:
        lines.insert(2, f"มีจุดที่อ่านไม่ชัด {warning_count} รายการ กรุณาตรวจบนหน้าเว็บ")

    usage_line = _format_token_usage(extracted)
    if usage_line:
        lines.append(usage_line)

    lines.extend([
        "",
        "ต้องการสแกนรูปถัดไปหรือจบครับ?",
        'กด "สแกนต่อ" หรือส่งรูปใหม่ได้เลย',
        'กด "จบ" เพื่อออกจากโหมดสแกน',
    ])

    if not PUBLIC_BASE_URL:
        lines.append(
            "หมายเหตุ: ตั้งค่า PUBLIC_BASE_URL ใน .env เพื่อให้ลิงก์เปิดได้จากมือถือ"
        )

    return {
        "type": "text",
        "text": "\n".join(lines),
        "quickReply": _build_continue_quick_reply(),
    }


def build_printout_page(token: str) -> str | None:
    printout = get_printout(token)
    if not printout:
        return None
    return render_printout_html(printout)
