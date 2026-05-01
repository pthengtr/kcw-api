import os
import hmac
import base64
import hashlib

import requests


LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_CONTENT_URL_BASE = "https://api-data.line.me/v2/bot/message"


def verify_line_signature(body: bytes, signature: str) -> bool:
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    expected_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected_signature, signature)


def download_line_message_content(message_id: str) -> tuple[bytes, str]:
    """
    Download binary content for LINE image/video/file message.

    For this feature we only call it for image messages.
    """
    if not message_id:
        raise ValueError("Missing LINE message_id")

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }

    url = f"{LINE_CONTENT_URL_BASE}/{message_id}/content"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    content_type = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
    return resp.content, content_type


def reply_line_payload(reply_token: str, messages: list[dict]):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }

    payload = {
        "replyToken": reply_token,
        "messages": messages,
    }

    resp = requests.post(LINE_REPLY_URL, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


def reply_line_message(reply_token: str, text: str):
    reply_line_payload(
        reply_token,
        [
            {
                "type": "text",
                "text": text[:5000],
            }
        ],
    )


def reply_line_image(reply_token: str, image_url: str, preview_url: str | None = None):
    preview = preview_url or image_url

    reply_line_payload(
        reply_token,
        [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": preview,
            }
        ],
    )


def reply_line_response(reply_token: str, response: dict | None):
    if not isinstance(response, dict):
        return reply_line_payload(
            reply_token,
            [
                {
                    "type": "text",
                    "text": "ระบบมีปัญหาชั่วคราวครับ",
                }
            ],
        )

    rtype = response.get("type")

    # multiple messages
    if rtype == "messages":
        msgs = response.get("messages") or []
        if not msgs:
            msgs = [{"type": "text", "text": "ไม่พบข้อมูลครับ"}]
        return reply_line_payload(reply_token, msgs)

    # single image
    if rtype == "image":
        url = response.get("originalContentUrl")
        if not url:
            return reply_line_payload(
                reply_token,
                [
                    {
                        "type": "text",
                        "text": "ไม่พบรูปสินค้า",
                    }
                ],
            )

        return reply_line_payload(
            reply_token,
            [
                {
                    "type": "image",
                    "originalContentUrl": url,
                    "previewImageUrl": response.get("previewImageUrl") or url,
                }
            ],
        )

    # ⭐ default text
    text = (response.get("text") or "ไม่เข้าใจคำสั่งครับ")[:5000]

    message = {
        "type": "text",
        "text": text,
    }

    if response.get("quickReply"):
        message["quickReply"] = response["quickReply"]

    return reply_line_payload(reply_token, [message])