import json
import re
from typing import Any

from src.handlers.ai_chat import AI_PATTERN, extract_ai_question
from src.ai.openai_kb import search_kb_candidates, get_kb_answer_by_id


MAX_KB_QUICK_REPLY = 10


def is_kb_select_postback(event: dict) -> bool:
    if event.get("type") != "postback":
        return False
    data = ((event.get("postback") or {}).get("data") or "").strip()
    return data.startswith("kb_select:")


def handle_kb_select_postback(engine, event: dict) -> dict:
    data = ((event.get("postback") or {}).get("data") or "").strip()
    kb_id = data.replace("kb_select:", "", 1).strip()

    if not kb_id:
        return {
            "type": "text",
            "text": "ไม่พบรายการที่เลือกครับ",
        }

    row = get_kb_answer_by_id(engine, kb_id)
    if not row:
        return {
            "type": "text",
            "text": "ไม่พบข้อมูลรายการนี้แล้วครับ",
        }

    title = (row.get("title") or "").strip()
    content = (row.get("content") or "").strip()

    text_parts = []
    if title:
        text_parts.append(title)
    if content:
        text_parts.append(content)

    final_text = "\n\n".join([p for p in text_parts if p]).strip() or "ไม่พบข้อมูลครับ"

    return {
        "type": "text",
        "text": final_text[:5000],
    }


def handle_kb_query_with_quick_reply(engine, user_text: str) -> dict:
    question = extract_ai_question(user_text)
    if not question:
        return {
            "type": "text",
            "text": (
                "เฮียช้าพร้อมครับ\n"
                "ลองพิมพ์แบบนี้:\n"
                "• เฮียช้า ลูกปืนคืออะไร\n"
                "• เฮียช้า ซีลหัวฉีดไทรทันมีอะไรบ้าง"
            ),
        }

    candidates = search_kb_candidates(engine, question, limit=MAX_KB_QUICK_REPLY)

    if not candidates:
        return {
            "type": "text",
            "text": "ยังไม่พบข้อมูลที่เกี่ยวข้องครับ",
        }

    lines = ["เจอหัวข้อใกล้เคียงครับ เลือกได้เลย:"]
    items = []

    for idx, row in enumerate(candidates[:MAX_KB_QUICK_REPLY], start=1):
        kb_id = str(row.get("id") or "").strip()
        title = (row.get("title") or "").strip() or f"หัวข้อ {idx}"

        # quick reply label should stay short/readable
        short_label = title[:20]

        lines.append(f"{idx}. {title}")

        items.append(
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": short_label,
                    "data": f"kb_select:{kb_id}",
                    "displayText": title[:300],
                },
            }
        )

    return {
        "type": "messages",
        "messages": [
            {
                "type": "text",
                "text": "\n".join(lines)[:5000],
                "quickReply": {
                    "items": items
                },
            }
        ],
    }