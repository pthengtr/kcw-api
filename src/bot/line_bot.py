import os
import hmac
import base64
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

import requests


LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_MULTICAST_URL = "https://api.line.me/v2/bot/message/multicast"
LINE_CONTENT_URL_BASE = "https://api-data.line.me/v2/bot/message"
LINE_PROFILE_URL_BASE = "https://api.line.me/v2/bot/profile"

# Bound for the duration of a webhook request so reply/download use the OA
# that signed the event. Outbound pushes (no binding) try every configured token.
_active_access_token: ContextVar[str | None] = ContextVar(
    "line_active_access_token", default=None
)


@dataclass(frozen=True)
class LineChannel:
    name: str
    secret: str
    access_token: str


def configured_line_channels() -> list[LineChannel]:
    """Primary + optional secondary Messaging API channel (OA migration).

    Primary: LINE_CHANNEL_SECRET / LINE_CHANNEL_ACCESS_TOKEN
    Secondary: LINE_CHANNEL_SECRET_2 / LINE_CHANNEL_ACCESS_TOKEN_2
    """
    channels: list[LineChannel] = []
    primary_secret = (os.getenv("LINE_CHANNEL_SECRET") or "").strip()
    primary_token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if primary_secret and primary_token:
        channels.append(
            LineChannel(
                name=(os.getenv("LINE_CHANNEL_NAME") or "primary").strip() or "primary",
                secret=primary_secret,
                access_token=primary_token,
            )
        )

    secondary_secret = (os.getenv("LINE_CHANNEL_SECRET_2") or "").strip()
    secondary_token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN_2") or "").strip()
    if secondary_secret and secondary_token:
        channels.append(
            LineChannel(
                name=(os.getenv("LINE_CHANNEL_NAME_2") or "secondary").strip()
                or "secondary",
                secret=secondary_secret,
                access_token=secondary_token,
            )
        )
    return channels


def _signature_for_secret(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def resolve_line_channel(body: bytes, signature: str) -> LineChannel | None:
    """Return the channel whose secret matches x-line-signature, if any."""
    if not signature:
        return None
    for channel in configured_line_channels():
        expected = _signature_for_secret(body, channel.secret)
        if hmac.compare_digest(expected, signature):
            return channel
    return None


def verify_line_signature(body: bytes, signature: str) -> bool:
    return resolve_line_channel(body, signature) is not None


@contextmanager
def use_line_channel(channel: LineChannel | None):
    """Bind reply/download/push during a webhook to this channel's token."""
    token = (channel.access_token if channel else "") or None
    reset = _active_access_token.set(token)
    try:
        yield channel
    finally:
        _active_access_token.reset(reset)


def find_line_channel(name: str | None) -> LineChannel | None:
    """Resolve a channel by name, slot alias, or 1-based index."""
    channels = configured_line_channels()
    if not channels:
        return None
    want = (name or "").strip().lower()
    if not want:
        return None
    if want in {"1", "primary", "default"}:
        return channels[0]
    if want in {"2", "secondary"}:
        return channels[1] if len(channels) > 1 else channels[0]
    for channel in channels:
        if channel.name.lower() == want:
            return channel
    return None


def outbound_line_channel(preference: str | None = None) -> LineChannel | None:
    """Pick the Messaging API channel for proactive push/multicast.

    ``preference`` (or the caller-provided env) may be a channel name, ``primary``,
    ``secondary``, ``new``, ``legacy``, or ``1``/``2``. When unset and two
    channels are configured, prefers secondary — the usual slot for a new OA
    added beside the legacy primary during migration.
    """
    channels = configured_line_channels()
    if not channels:
        return None
    want = (preference or "").strip().lower()
    if want in {"new"}:
        # Convention: secondary is the newly added OA when dual-configured.
        return channels[1] if len(channels) > 1 else channels[0]
    if want in {"legacy", "old"}:
        return channels[0]
    found = find_line_channel(want) if want else None
    if found:
        return found
    if len(channels) > 1:
        return channels[1]
    return channels[0]


def _channel_secret() -> str:
    # Read at call time. CLI jobs load .env after this module is imported.
    channels = configured_line_channels()
    return channels[0].secret if channels else ""


def _access_token() -> str:
    active = _active_access_token.get()
    if active:
        return active
    channels = configured_line_channels()
    return channels[0].access_token if channels else ""


def _access_tokens_to_try() -> list[str]:
    active = _active_access_token.get()
    if active:
        return [active]
    channels = configured_line_channels()
    if not channels:
        return []
    # Prefer the outbound/"new" OA first so proactive pushes land on bot v2
    # when dual channels are configured, then fall back to the rest.
    preferred = outbound_line_channel(os.getenv("LINE_OUTBOUND_CHANNEL") or "new")
    ordered: list[LineChannel] = []
    if preferred is not None:
        ordered.append(preferred)
    for channel in channels:
        if channel not in ordered:
            ordered.append(channel)
    tokens: list[str] = []
    seen: set[str] = set()
    for channel in ordered:
        token = channel.access_token
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }


def _is_retryable_wrong_channel(exc: requests.HTTPError) -> bool:
    resp = getattr(exc, "response", None)
    if resp is None:
        return False
    # Wrong OA for this user id / message id → try the other channel.
    # 429 (monthly quota) on one OA should also fall through to the next.
    return resp.status_code in (400, 404, 429)


def download_line_message_content(message_id: str) -> tuple[bytes, str]:
    """
    Download binary content for LINE image/video/file message.

    For this feature we only call it for image messages.
    """
    if not message_id:
        raise ValueError("Missing LINE message_id")

    url = f"{LINE_CONTENT_URL_BASE}/{message_id}/content"
    last_error: Exception | None = None
    for token in _access_tokens_to_try():
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            last_error = exc
            if _is_retryable_wrong_channel(exc):
                continue
            raise
        content_type = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
        return resp.content, content_type
    if last_error:
        raise last_error
    raise RuntimeError("No LINE channel access token configured")


def reply_line_payload(reply_token: str, messages: list[dict]):
    headers = _auth_headers(_access_token())
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

    payload = {
        "to": to,
        "messages": messages[:5],
    }
    last_error: Exception | None = None
    for token in _access_tokens_to_try():
        headers = _auth_headers(token)
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=15)
        try:
            resp.raise_for_status()
            return
        except requests.HTTPError as exc:
            last_error = exc
            if _is_retryable_wrong_channel(exc):
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("No LINE channel access token configured")


def multicast_line_messages(to: list[str], messages: list[dict]) -> list[str]:
    """Push the same messages to many users in one API call.

    LINE still counts one message per recipient toward the monthly quota.
    Returns the de-duplicated recipient ids that were sent to.

    With two OAs configured, recipients may belong to either bot, so delivery
    falls back to per-user push (each tries every channel token).
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

    tokens = _access_tokens_to_try()
    if len(tokens) <= 1:
        headers = _auth_headers(tokens[0] if tokens else _access_token())
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

    # Mixed OA user ids: multicast cannot mix channels in one request.
    delivered: list[str] = []
    errors: list[Exception] = []
    for uid in recipients:
        try:
            push_line_messages(uid, messages)
            delivered.append(uid)
        except Exception as exc:  # noqa: BLE001 — keep delivering the rest
            errors.append(exc)
            print(f"LINE multicast fan-out failed for {uid}: {exc}")
    if not delivered and errors:
        raise errors[0]
    return delivered


def push_line_message(to: str, text: str):
    push_line_messages(to, [{"type": "text", "text": (text or "")[:5000]}])


def fetch_line_display_name(line_user_id: str) -> str | None:
    if not line_user_id:
        return None

    url = f"{LINE_PROFILE_URL_BASE}/{line_user_id}"
    for token in _access_tokens_to_try():
        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                return (resp.json() or {}).get("displayName")
            if resp.status_code in (400, 404):
                continue
            print("LINE profile fetch failed:", resp.text)
            return None
        except Exception as e:
            print("LINE profile error:", e)
            return None
    return None


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
