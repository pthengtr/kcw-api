import os
import re
import time
from urllib.parse import quote

from supabase import create_client, Client

from src.bot.line_bot import download_line_message_content


SUPABASE_URL = os.getenv("SUPABASE_DB_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_IMAGE_BUCKET = os.getenv("SUPABASE_IMAGE_BUCKET", "pictures")
SUPABASE_IMAGE_BASE_FOLDER = os.getenv("SUPABASE_IMAGE_BASE_FOLDER", "product").strip("/")

MAX_PRODUCT_IMAGES = 5
IMAGE_SESSION_TTL_SECONDS = int(os.getenv("LINE_IMAGE_UPLOAD_SESSION_TTL_SECONDS", "600"))

UPLOAD_SESSIONS: dict[str, dict] = {}
DELETE_SESSIONS: dict[str, dict] = {}

END_SESSION_WORDS = {
    "เสร็จ",
    "จบ",
    "done",
    "ยกเลิก",
    "cancel",
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_product_image_folder(bcode: str) -> str:
    bcode = normalize_bcode(bcode).strip("/")
    if not bcode:
        return ""

    if SUPABASE_IMAGE_BASE_FOLDER:
        return f"{SUPABASE_IMAGE_BASE_FOLDER}/{bcode}"

    return bcode

def build_public_storage_url(bucket: str, path: str, version: str | None = None) -> str:
    path = path.lstrip("/")
    url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"

    # fixed filenames may be cached; version query helps LINE fetch fresh image
    if version:
        url = f"{url}?v={quote(str(version), safe='')}"

    return url


def normalize_bcode(value: str | None) -> str:
    return (value or "").strip()


def expected_product_image_names(bcode: str) -> list[str]:
    bcode = normalize_bcode(bcode)
    return [
        f"{bcode}.jpg",
        f"{bcode}_2.jpg",
        f"{bcode}_3.jpg",
        f"{bcode}_4.jpg",
        f"{bcode}_5.jpg",
    ]


def expected_product_image_paths(bcode: str) -> list[str]:
    folder = get_product_image_folder(bcode)
    return [f"{folder}/{name}" for name in expected_product_image_names(bcode)]


def _now() -> float:
    return time.time()


def _is_expired(session: dict | None) -> bool:
    if not session:
        return True
    return float(session.get("expires_at") or 0) < _now()


def _get_active_session(store: dict[str, dict], line_user_id: str | None) -> dict | None:
    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return None

    session = store.get(line_user_id)
    if _is_expired(session):
        store.pop(line_user_id, None)
        return None

    return session


def _clear_session(store: dict[str, dict], line_user_id: str | None):
    line_user_id = (line_user_id or "").strip()
    if line_user_id:
        store.pop(line_user_id, None)


def _extend_session(session: dict):
    session["expires_at"] = _now() + IMAGE_SESSION_TTL_SECONDS


def _item_timestamp(item: dict) -> str:
    return (
        item.get("updated_at")
        or item.get("created_at")
        or item.get("last_modified")
        or ""
    )


def _list_expected_image_items(bcode: str) -> list[dict]:
    bcode = normalize_bcode(bcode)
    if not bcode:
        return []

    folder = get_product_image_folder(bcode)
    expected_names = expected_product_image_names(bcode)
    expected_set = set(expected_names)

    try:
        items = supabase.storage.from_(SUPABASE_IMAGE_BUCKET).list(folder)
    except Exception as e:
        print("SUPABASE IMAGE LIST ERROR:", e)
        return []

    if not items:
        return []

    results = []
    for item in items:
        name = item.get("name", "")
        if name not in expected_set:
            continue

        copied = dict(item)
        copied["path"] = f"{folder}/{name}"
        copied["slot_no"] = expected_names.index(name) + 1
        copied["version"] = _item_timestamp(copied)
        results.append(copied)

    results.sort(key=lambda x: x.get("slot_no", 999))
    return results


def list_product_images(bcode: str, max_images: int = MAX_PRODUCT_IMAGES) -> list[str]:
    items = _list_expected_image_items(bcode)
    return [item["path"] for item in items[:max_images]]


def _list_product_image_messages(bcode: str, max_images: int = MAX_PRODUCT_IMAGES) -> list[dict]:
    items = _list_expected_image_items(bcode)

    messages = []
    for item in items[:max_images]:
        url = build_public_storage_url(
            SUPABASE_IMAGE_BUCKET,
            item["path"],
            version=item.get("version"),
        )
        messages.append(
            {
                "type": "image",
                "originalContentUrl": url,
                "previewImageUrl": url,
            }
        )

    return messages


def is_image_command(text: str) -> bool:
    t = (text or "").strip().lower()

    return (
        t == "img"
        or t.startswith("img ")
        or t == "รูป"
        or t.startswith("รูป ")
        or t == "ภาพ"
        or t.startswith("ภาพ ")
        or t == "เพิ่มรูป"
        or t.startswith("เพิ่มรูป ")
        or t == "ลบรูป"
        or t.startswith("ลบรูป ")
    )


def _is_upload_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return t == "เพิ่มรูป" or t.startswith("เพิ่มรูป ")


def _is_delete_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return t == "ลบรูป" or t.startswith("ลบรูป ")


def _extract_delete_selection(text: str) -> int | None:
    t = (text or "").strip()
    m = re.match(r"^ลบรูป\s+([1-5])$", t)
    if not m:
        return None
    return int(m.group(1))


def extract_image_key(text: str) -> str | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip()


def _start_upload_session(line_user_id: str, bcode: str):
    _clear_session(DELETE_SESSIONS, line_user_id)

    UPLOAD_SESSIONS[line_user_id] = {
        "bcode": bcode,
        "expires_at": _now() + IMAGE_SESSION_TTL_SECONDS,
        "uploaded_count": 0,
    }


def _start_delete_session(line_user_id: str, bcode: str, image_paths: list[str]):
    _clear_session(UPLOAD_SESSIONS, line_user_id)

    DELETE_SESSIONS[line_user_id] = {
        "bcode": bcode,
        "image_paths": image_paths,
        "expires_at": _now() + IMAGE_SESSION_TTL_SECONDS,
    }

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


def _build_upload_session_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            _qr_camera_roll("เลือกรูป"),
            _qr_camera("ถ่ายรูป"),
            _qr_message("เสร็จ", "เสร็จ"),
        ]
    }


def _build_after_upload_done_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            _qr_message("เช็คสินค้า", f"เช็ค {bcode}"),
            _qr_message("ดูรูป", f"รูป {bcode}"),
            _qr_message("ลบรูป", f"ลบรูป {bcode}"),
            _qr_message("เพิ่มรูป", f"เพิ่มรูป {bcode}"),
        ]
    }


def _build_no_image_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            _qr_message("เช็คสินค้า", f"เช็ค {bcode}"),
            _qr_message("เพิ่มรูป", f"เพิ่มรูป {bcode}"),
        ]
    }


def _build_view_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "เพิ่มรูป",
                    "text": f"เพิ่มรูป {bcode}",
                },
            },
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "ลบรูป",
                    "text": f"ลบรูป {bcode}",
                },
            },
        ]
    }

def _build_delete_quick_reply(image_count: int) -> dict:
    items = []

    for i in range(1, image_count + 1):
        items.append(
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": f"ลบรูป {i}",
                    "text": f"ลบรูป {i}",
                },
            }
        )

    items.append(
        {
            "type": "action",
            "action": {
                "type": "message",
                "label": "เสร็จ",
                "text": "เสร็จ",
            },
        }
    )

    return {"items": items}


def _select_upload_target(bcode: str) -> tuple[str, bool, str | None]:
    bcode = normalize_bcode(bcode)
    folder = get_product_image_folder(bcode)

    existing_items = _list_expected_image_items(bcode)
    existing_names = {item.get("name") for item in existing_items}

    for name in expected_product_image_names(bcode):
        if name not in existing_names:
            return f"{folder}/{name}", False, None

    oldest_item = sorted(
        existing_items,
        key=lambda item: (_item_timestamp(item), item.get("slot_no", 999)),
    )[0]

    return oldest_item["path"], True, oldest_item.get("name")

def _build_delete_preview_response(
    bcode: str,
    image_items: list[dict],
    success_text: str | None = None,
) -> dict:
    """
    Build delete-preview reply.

    Important LINE behavior:
    - Quick reply should be attached to the last message object.
    - If quick reply is attached to an earlier message and the bot sends more
      messages after it, LINE may hide/remove the quick reply.
    """
    if not image_items:
        return {
            "type": "text",
            "text": success_text or f"ไม่พบรูปสินค้าสำหรับ {bcode} ครับ",
        }

    messages = []

    if success_text:
        messages.append(
            {
                "type": "text",
                "text": success_text,
            }
        )

    for item in image_items[:MAX_PRODUCT_IMAGES]:
        url = build_public_storage_url(
            SUPABASE_IMAGE_BUCKET,
            item["path"],
            version=item.get("version"),
        )
        messages.append(
            {
                "type": "image",
                "originalContentUrl": url,
                "previewImageUrl": url,
            }
        )

    # Attach quick reply to the LAST message, not the text message.
    # This keeps it visible after all image messages are sent.
    if messages:
        messages[-1]["quickReply"] = _build_delete_quick_reply(len(image_items))

    return {
        "type": "messages",
        "messages": messages[:5],
    }

def upload_product_image(bcode: str, image_bytes: bytes, content_type: str | None = None) -> dict:
    bcode = normalize_bcode(bcode)
    if not bcode:
        raise ValueError("Missing bcode")

    if not image_bytes:
        raise ValueError("Empty image content")

    target_path, replaced, replaced_name = _select_upload_target(bcode)

    file_options = {
        "content-type": content_type or "image/jpeg",
        "cache-control": "3600",
        "upsert": "true",
    }

    try:
        supabase.storage.from_(SUPABASE_IMAGE_BUCKET).upload(
            target_path,
            image_bytes,
            file_options=file_options,
        )
    except Exception as e:
        # Fallback for storage clients/environments where upsert is not honored.
        print("SUPABASE IMAGE UPSERT ERROR, TRY REMOVE+UPLOAD:", e)
        try:
            supabase.storage.from_(SUPABASE_IMAGE_BUCKET).remove([target_path])
        except Exception as remove_err:
            print("SUPABASE IMAGE REMOVE BEFORE RETRY ERROR:", remove_err)

        retry_options = {
            "content-type": content_type or "image/jpeg",
            "cache-control": "3600",
        }

        supabase.storage.from_(SUPABASE_IMAGE_BUCKET).upload(
            target_path,
            image_bytes,
            file_options=retry_options,
        )

    return {
        "bcode": bcode,
        "path": target_path,
        "filename": target_path.rsplit("/", 1)[-1],
        "replaced": replaced,
        "replaced_name": replaced_name,
    }


def handle_image_session_text(line_user_id: str | None, text: str) -> dict | None:
    """
    Intercept text while user is inside image upload/delete session.

    Return None if there is no active image session.
    """
    line_user_id = (line_user_id or "").strip()
    t = (text or "").strip()
    t_lower = t.lower()

    delete_session = _get_active_session(DELETE_SESSIONS, line_user_id)
    if delete_session:
        bcode = delete_session.get("bcode", "")

        if t_lower in END_SESSION_WORDS:
            _clear_session(DELETE_SESSIONS, line_user_id)
            return {
                "type": "text",
                "text": f"จบการลบรูปสินค้า {bcode} แล้วครับ\nต้องการทำอะไรต่อ?",
                "quickReply": _build_after_upload_done_quick_reply(bcode),
            }

        selected_no = _extract_delete_selection(t)
        if selected_no is not None:
            image_paths = delete_session.get("image_paths") or []
            index = selected_no - 1

            if index < 0 or index >= len(image_paths):
                return {
                    "type": "text",
                    "text": "ไม่พบรูปตามหมายเลขที่เลือกครับ",
                    "quickReply": _build_delete_quick_reply(len(image_paths)),
                }

            path = image_paths[index]

            try:
                supabase.storage.from_(SUPABASE_IMAGE_BUCKET).remove([path])
            except Exception as e:
                print("SUPABASE IMAGE DELETE ERROR:", e)
                return {
                    "type": "text",
                    "text": "ลบรูปไม่สำเร็จครับ กรุณาลองใหม่อีกครั้ง",
                    "quickReply": _build_delete_quick_reply(len(image_paths)),
                }

            # Refresh current images after deletion
            refreshed_items = _list_expected_image_items(bcode)
            refreshed_paths = [item["path"] for item in refreshed_items]

            # If no image remains, end delete session
            if not refreshed_paths:
                _clear_session(DELETE_SESSIONS, line_user_id)
                return {
                    "type": "text",
                    "text": f"ลบรูปที่ {selected_no} ของสินค้า {bcode} แล้วครับ ✅\nตอนนี้ไม่เหลือรูปแล้วครับ",
                    "quickReply": _build_no_image_quick_reply(bcode),
                }

            # Keep delete session alive so user can continue deleting
            delete_session["image_paths"] = refreshed_paths
            _extend_session(delete_session)

            success_text = (
                f"ลบรูปที่ {selected_no} ของสินค้า {bcode} แล้วครับ ✅\n"
                "ต้องการลบรูปไหนต่อ เลือกได้เลยครับ"
            )

            return _build_delete_preview_response(
                bcode,
                refreshed_items,
                success_text=success_text,
            )

        return {
            "type": "text",
            "text": (
                f"ตอนนี้อยู่ในโหมดลบรูปสินค้า {bcode} ครับ\n"
                'กรุณาเลือกปุ่ม "ลบรูป 1-5" หรือพิมพ์ "เสร็จ" เพื่อจบ'
            ),
            "quickReply": _build_delete_quick_reply(
                len(delete_session.get("image_paths") or [])
            ),
        }
    
    upload_session = _get_active_session(UPLOAD_SESSIONS, line_user_id)
    if upload_session:
        bcode = upload_session.get("bcode", "")

        if t_lower in END_SESSION_WORDS:
            _clear_session(UPLOAD_SESSIONS, line_user_id)
            return {
                "type": "text",
                "text": f"จบการเพิ่มรูปสินค้า {bcode} แล้วครับ\nต้องการทำอะไรต่อ?",
                "quickReply": _build_after_upload_done_quick_reply(bcode),
            }

        return {
            "type": "text",
            "text": (
                f"ตอนนี้อยู่ในโหมดเพิ่มรูปสินค้า {bcode} ครับ\n"
                'กรุณาส่งรูปภาพ หรือกด "เสร็จ" เพื่อจบ'
            ),
            "quickReply": _build_upload_session_quick_reply(bcode),
        }

    if _extract_delete_selection(t) is not None:
        return {
            "type": "text",
            "text": "ไม่มีรายการรอลบรูปครับ กรุณาพิมพ์ ลบรูป [รหัสสินค้า] ก่อน",
        }

    return None


def handle_line_image_message(line_user_id: str | None, message_id: str | None) -> dict:
    line_user_id = (line_user_id or "").strip()

    upload_session = _get_active_session(UPLOAD_SESSIONS, line_user_id)
    if not upload_session:
        return {
            "type": "text",
            "text": "ถ้าต้องการเพิ่มรูปสินค้า กรุณาพิมพ์ เพิ่มรูป [รหัสสินค้า] ก่อนครับ",
        }

    bcode = upload_session.get("bcode", "")
    if not bcode:
        _clear_session(UPLOAD_SESSIONS, line_user_id)
        return {
            "type": "text",
            "text": "ไม่พบรหัสสินค้าใน session ครับ กรุณาพิมพ์ เพิ่มรูป [รหัสสินค้า] อีกครั้ง",
        }

    try:
        image_bytes, content_type = download_line_message_content(message_id or "")
        result = upload_product_image(bcode, image_bytes, content_type=content_type)
    except Exception as e:
        print("LINE IMAGE UPLOAD ERROR:", e)
        return {
            "type": "text",
            "text": (
                f"เพิ่มรูปสินค้า {bcode} ไม่สำเร็จครับ\n"
                'กรุณาส่งรูปใหม่อีกครั้ง หรือกด "เสร็จ" เพื่อจบ'
            ),
            "quickReply": _build_upload_session_quick_reply(bcode),
        }

    upload_session["uploaded_count"] = int(upload_session.get("uploaded_count") or 0) + 1
    _extend_session(upload_session)

    if result["replaced"]:
        detail = f"ครบ 5 รูปแล้ว จึงแทนรูปเก่าสุด: {result['replaced_name']}"
    else:
        detail = f"บันทึกเป็นไฟล์: {result['filename']}"

    return {
        "type": "text",
        "text": (
            f"เพิ่มรูปให้ {bcode} แล้ว ✅\n"
            f"{detail}\n"
            'ส่งรูปต่อได้เลย หรือกด "เสร็จ" เพื่อจบ'
        ),
        "quickReply": _build_upload_session_quick_reply(bcode),
    }


def handle_start_upload_command(text: str, line_user_id: str | None) -> dict:
    bcode = normalize_bcode(extract_image_key(text))
    if not bcode:
        return {
            "type": "text",
            "text": "กรุณาระบุรหัสสินค้า เช่น เพิ่มรูป 22010585",
        }

    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return {
            "type": "text",
            "text": "ไม่พบ LINE user id จึงเริ่มโหมดเพิ่มรูปไม่ได้ครับ",
        }

    _start_upload_session(line_user_id, bcode)

    return {
        "type": "text",
        "text": (
            f"ส่งรูปสินค้า {bcode} ได้เลยครับ\n"
            "ส่งได้หลายรูป ระบบจะอัปโหลดทันทีทีละรูป\n"
            'กดเลือกรูป / ถ่ายรูป หรือกด "เสร็จ" เพื่อจบ'
        ),
        "quickReply": _build_upload_session_quick_reply(bcode),
    }


def handle_delete_image_command(text: str, line_user_id: str | None) -> dict:
    bcode = normalize_bcode(extract_image_key(text))
    if not bcode:
        return {
            "type": "text",
            "text": "กรุณาระบุรหัสสินค้า เช่น ลบรูป 22010585",
        }

    line_user_id = (line_user_id or "").strip()
    if not line_user_id:
        return {
            "type": "text",
            "text": "ไม่พบ LINE user id จึงเริ่มโหมดลบรูปไม่ได้ครับ",
        }

    image_items = _list_expected_image_items(bcode)
    image_paths = [item["path"] for item in image_items]

    if not image_paths:
        return {
            "type": "text",
            "text": f"ไม่พบรูปสินค้าสำหรับ {bcode} ครับ",
            "quickReply": _build_no_image_quick_reply(bcode),
        }

    _start_delete_session(line_user_id, bcode, image_paths)

    return _build_delete_preview_response(bcode, image_items)

def handle_view_image_command(text: str) -> dict:
    bcode = normalize_bcode(extract_image_key(text))
    if not bcode:
        return {
            "type": "text",
            "text": "กรุณาระบุรหัสสินค้า เช่น รูป 22010585",
        }

    image_messages = _list_product_image_messages(bcode, max_images=MAX_PRODUCT_IMAGES)

    # No image case: still offer เพิ่มรูป immediately.
    if not image_messages:
        return {
            "type": "messages",
            "messages": [
                {
                    "type": "text",
                    "text": f"ไม่พบรูปสินค้าสำหรับ {bcode} ครับ",
                    "quickReply": _build_view_quick_reply(bcode),
                }
            ],
        }

    # If 5 images exist, do not add text header because LINE reply limit is 5.
    # Attach quick reply to the last image.
    if len(image_messages) >= MAX_PRODUCT_IMAGES:
        image_messages[-1]["quickReply"] = _build_view_quick_reply(bcode)
        return {
            "type": "messages",
            "messages": image_messages,
        }

    messages = [
        {
            "type": "text",
            "text": f"รูปสินค้า {bcode} ({len(image_messages)} รูป)",
        },
        *image_messages,
    ]

    # Quick reply should be attached to the last message object.
    messages[-1]["quickReply"] = _build_view_quick_reply(bcode)

    return {
        "type": "messages",
        "messages": messages,
    }

def handle_image_command(text: str, line_user_id: str | None = None) -> dict:
    if _is_upload_command(text):
        return handle_start_upload_command(text, line_user_id=line_user_id)

    selected_no = _extract_delete_selection(text)
    if selected_no is not None:
        return {
            "type": "text",
            "text": "ไม่มีรายการรอลบรูปครับ กรุณาพิมพ์ ลบรูป [รหัสสินค้า] ก่อน",
        }

    if _is_delete_command(text):
        return handle_delete_image_command(text, line_user_id=line_user_id)

    return handle_view_image_command(text)