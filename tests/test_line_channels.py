import base64
import hashlib
import hmac

import requests

import src.bot.line_bot as line_bot


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_configured_channels_primary_only(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.delenv("LINE_CHANNEL_SECRET_2", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN_2", raising=False)

    channels = line_bot.configured_line_channels()
    assert len(channels) == 1
    assert channels[0].name == "primary"
    assert channels[0].access_token == "tok-a"


def test_configured_channels_primary_and_secondary(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_NAME", "new-oa")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")
    monkeypatch.setenv("LINE_CHANNEL_NAME_2", "old-oa")

    channels = line_bot.configured_line_channels()
    assert [(c.name, c.secret, c.access_token) for c in channels] == [
        ("new-oa", "sec-a", "tok-a"),
        ("old-oa", "sec-b", "tok-b"),
    ]


def test_resolve_picks_secondary_signature(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    body = b'{"events":[]}'
    channel = line_bot.resolve_line_channel(body, _sign(body, "sec-b"))
    assert channel is not None
    assert channel.name == "secondary"
    assert channel.access_token == "tok-b"
    assert line_bot.verify_line_signature(body, _sign(body, "sec-a"))
    assert not line_bot.verify_line_signature(body, "bogus")


def test_reply_uses_bound_channel_token(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["auth"] = headers["Authorization"]
        return _Resp()

    monkeypatch.setattr(line_bot.requests, "post", fake_post)
    channel = line_bot.LineChannel("old-oa", "sec-b", "tok-b")
    with line_bot.use_line_channel(channel):
        line_bot.reply_line_message("reply-token", "hello")

    assert captured["auth"] == "Bearer tok-b"


def test_push_falls_back_to_second_token(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    attempts: list[str] = []

    class _Resp:
        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                err = requests.HTTPError(response=self)
                raise err

    def fake_post(url, headers=None, json=None, timeout=None):
        auth = headers["Authorization"]
        attempts.append(auth)
        if auth == "Bearer tok-a":
            return _Resp(400)
        return _Resp(200)

    monkeypatch.setattr(line_bot.requests, "post", fake_post)
    line_bot.push_line_message("U-legacy", "hi")
    assert attempts == ["Bearer tok-a", "Bearer tok-b"]


def test_multicast_with_two_channels_fans_out(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    pushed: list[str] = []

    def fake_push(to, messages):
        pushed.append(to)

    monkeypatch.setattr(line_bot, "push_line_messages", fake_push)
    delivered = line_bot.multicast_line_messages(
        ["U1", "U2"], [{"type": "text", "text": "hi"}]
    )
    assert delivered == ["U1", "U2"]
    assert pushed == ["U1", "U2"]


def test_outbound_prefers_secondary_as_new(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    channel = line_bot.outbound_line_channel("new")
    assert channel is not None
    assert channel.access_token == "tok-b"

    legacy = line_bot.outbound_line_channel("legacy")
    assert legacy is not None
    assert legacy.access_token == "tok-a"


def test_fetch_display_name_tries_both_tokens(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-a")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-a")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-b")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-b")

    calls: list[str] = []

    class _Resp:
        def __init__(self, status, payload=None):
            self.status_code = status
            self._payload = payload or {}
            self.text = "err"

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None):
        auth = headers["Authorization"]
        calls.append(auth)
        if auth == "Bearer tok-a":
            return _Resp(404)
        return _Resp(200, {"displayName": "Peung"})

    monkeypatch.setattr(line_bot.requests, "get", fake_get)
    assert line_bot.fetch_line_display_name("U-old") == "Peung"
    assert calls == ["Bearer tok-a", "Bearer tok-b"]
