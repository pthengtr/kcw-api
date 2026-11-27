import os
import hmac
import base64
import hashlib

import requests


LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_MULTICAST_URL = "https://api.line.me/v2/bot/message/multicast"
LINE_CONTENT_URL_BASE = "https://api-data.line.me/v2/bot/message"


def _channel_secret() -> str:
    # Read at call time. CLI jobs load .env after this module is imported.
    return (os.getenv("LINE_CHANNEL_SECRET") or "").strip()


def _access_token() -> str:
    return (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()


def verify_line_signature(body: bytes, signature: str) -> bool:
    digest = hmac.new(
        _channel_secret().encode("utf-8"),
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
        "Authorization": f"Bearer {_access_token()}",
    }

    url = f"{LINE_CONTENT_URL_BASE}/{message_id}/content"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    content_type = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
    return resp.content, content_type


def reply_line_payload(reply_token: str, messages: list[dict]):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_access_token()}",
    }

    payload = {
        "replyToken": reply_token,
        "messages": messages,
    }

    resp = requests.post(LINE_REPLY_URL, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


def push_line_messages(to: str, messages: list[dict]):
    if not (to or "").strip():
        raise ValueError("Missing LINE user id")
    if not messages:
        raise ValueError("Missing LINE messages")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_access_token()}",
    }
    payload = {
        "to": to,
        "messages": messages[:5],
    }
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


def multicast_line_messages(to: list[str], messages: list[dict]) -> list[str]:
    """Push the same messages to many users in one API call.

    LINE still counts one message per recipient toward the monthly quota.
    Returns the de-duplicated recipient ids that were sent to.
    """
    recipients = []
    seen: set[str] = set()
    for uid in to or []:
        uid = (uid or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        recipients.append(uid)
    if not recipients:
        raise ValueError("Missing LINE user ids")
    if not messages:
        raise ValueError("Missing LINE messages")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_access_token()}",
    }
    # LINE multicast accepts at most 500 user ids per request.
    for i in range(0, len(recipients), 500):
        chunk = recipients[i : i + 500]
        payload = {
            "to": chunk,
            "messages": messages[:5],
        }
        resp = requests.post(
            LINE_MULTICAST_URL, headers=headers, json=payload, timeout=15
        )
        resp.raise_for_status()
    return recipients


def push_line_message(to: str, text: str):
    push_line_messages(to, [{"type": "text", "text": (text or "")[:5000]}])


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

    # buttons / confirm / carousel template (hides long URIs behind labels)
    if rtype == "template":
        return reply_line_payload(reply_token, [response])

    # flex message (Thai word-links over long entry URLs)
    if rtype == "flex":
        return reply_line_payload(reply_token, [response])

    # ⭐ default text
    text = (response.get("text") or "ไม่เข้าใจคำสั่งครับ")[:5000]

    message = {
        "type": "text",
        "text": text,
    }

    if response.get("quickReply"):
        message["quickReply"] = response["quickReply"]

    return reply_line_payload(reply_token, [message])