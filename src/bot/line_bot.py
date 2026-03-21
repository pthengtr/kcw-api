import os
import hmac
import base64
import hashlib
import requests

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def verify_line_signature(body: bytes, signature: str) -> bool:
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected_signature, signature)


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
    reply_line_payload(reply_token, [
        {
            "type": "text",
            "text": text[:5000],
        }
    ])


def reply_line_image(reply_token: str, image_url: str, preview_url: str | None = None):
    preview = preview_url or image_url

    reply_line_payload(reply_token, [
        {
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": preview,
        }
    ])