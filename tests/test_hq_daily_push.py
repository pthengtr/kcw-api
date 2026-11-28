import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import src.bot.line_bot as line_bot
import src.hq_daily_push as hq_daily_push
from src.hq_daily_push import (
    fail_names,
    format_hq_failure,
    log_excerpt,
    ok_names,
    outbound_preference,
    push_to,
)
from src.tar_transfer.push import line_user_ids_for_names, name_tokens


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        return _Result(self._rows)


class _Engine:
    def __init__(self, rows):
        self._rows = rows

    def connect(self):
        return _Connection(self._rows)


ROWS = [
    ("Upeung", "peung"),
    ("Uphu", "PHU Nattapon W."),
    ("Uice", "January Ice"),
    ("Uturbo", "TURBO"),
    ("Uother", "Nu"),
]


def test_names_match_display_words():
    engine = _Engine(ROWS)
    assert line_user_ids_for_names(engine, ["peung", "phu", "ice"]) == [
        "Upeung",
        "Uphu",
        "Uice",
    ]
    assert line_user_ids_for_names(engine, ["peung", "turbo"]) == ["Upeung", "Uturbo"]
    assert "ice" in name_tokens("January Ice")
    assert "phu" in name_tokens("PHU Nattapon W.")


def test_push_reads_token_set_after_import(monkeypatch):
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["auth"] = headers["Authorization"]
        return _Resp()

    monkeypatch.setenv("LINE_CHANNEL_SECRET", "late-secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "late-token")
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN_2", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_SECRET_2", raising=False)
    monkeypatch.delenv("LINE_OUTBOUND_CHANNEL", raising=False)
    monkeypatch.setattr(line_bot.requests, "post", fake_post)
    line_bot.push_line_message("U1", "hi")
    assert captured["auth"] == "Bearer late-token"


def test_default_recipients(monkeypatch):
    monkeypatch.delenv("HQ_DAILY_PUSH_NAMES", raising=False)
    monkeypatch.delenv("HQ_DAILY_PUSH_FAIL_NAMES", raising=False)
    assert ok_names() == ["peung", "phu", "ice"]
    assert fail_names() == ["peung", "turbo"]


def test_ok_push_uses_today_before_seven_pm(monkeypatch):
    fixed = datetime(2026, 11, 1, 16, 30, tzinfo=ZoneInfo("Asia/Bangkok"))

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    captured = {}

    monkeypatch.setattr(hq_daily_push, "datetime", _FrozenDateTime)
    monkeypatch.setattr(hq_daily_push, "get_engine", lambda: object())
    monkeypatch.setattr(
        hq_daily_push,
        "handle_sales_query",
        lambda engine, text: captured.setdefault("text", text),
    )
    monkeypatch.setattr(
        hq_daily_push,
        "push_to",
        lambda engine, names, message: message,
    )

    assert hq_daily_push.push_ok() == "ยอดขาย 2026-11-01"
    assert captured["text"] == "ยอดขาย 2026-11-01"


def test_failure_message_includes_step_and_log(tmp_path):
    log = tmp_path / "step.log"
    log.write_text("noise\nFAILED: vat inventory\n", encoding="utf-8")
    text = format_hq_failure("vat inventory", 1, log_excerpt(str(log)))
    assert text.startswith("HQ ประจำวันรันไม่สำเร็จ")
    assert "ขั้นตอน: vat inventory" in text
    assert "exit 1" in text
    assert "FAILED: vat inventory" in text
    assert "ยอดขาย" not in text


def test_outbound_defaults_to_new(monkeypatch):
    monkeypatch.delenv("HQ_DAILY_LINE_CHANNEL", raising=False)
    monkeypatch.delenv("LINE_OUTBOUND_CHANNEL", raising=False)
    assert outbound_preference() == "new"
    monkeypatch.setenv("HQ_DAILY_LINE_CHANNEL", "secondary")
    assert outbound_preference() == "secondary"


def test_push_to_prefers_bot_v2_without_bind(monkeypatch):
    monkeypatch.setenv("HQ_DAILY_LINE_CHANNEL", "new")
    monkeypatch.delenv("LINE_OUTBOUND_CHANNEL", raising=False)

    class _Channel:
        name = "secondary"

    seen_outbound: list[str | None] = []
    sent = []

    def fake_push(uid, text):
        seen_outbound.append(os.environ.get("LINE_OUTBOUND_CHANNEL"))
        sent.append((uid, text))

    monkeypatch.setattr(
        hq_daily_push,
        "line_user_ids_for_names",
        lambda engine, names: ["Upeung", "Uphu"],
    )
    monkeypatch.setattr(hq_daily_push, "outbound_line_channel", lambda pref: _Channel())
    monkeypatch.setattr(hq_daily_push, "push_line_message", fake_push)

    result = push_to(object(), ["peung", "phu"], "ยอดขาย test")
    assert result == "pushed to 2 user(s) via secondary"
    assert seen_outbound == ["new", "new"]
    assert os.environ.get("LINE_OUTBOUND_CHANNEL") is None
    assert sent == [("Upeung", "ยอดขาย test"), ("Uphu", "ยอดขาย test")]


def test_push_to_soft_fails_on_quota_429(monkeypatch):
    monkeypatch.delenv("HQ_DAILY_LINE_CHANNEL", raising=False)
    monkeypatch.delenv("LINE_OUTBOUND_CHANNEL", raising=False)
    monkeypatch.setattr(
        hq_daily_push,
        "line_user_ids_for_names",
        lambda engine, names: ["Upeung"],
    )

    class _Resp:
        status_code = 429

    def boom(uid, text):
        raise requests.HTTPError("429", response=_Resp())

    monkeypatch.setattr(hq_daily_push, "push_line_message", boom)
    result = push_to(object(), ["peung"], "ยอดขาย test")
    assert "quota 429" in result
    assert "bot v2" in result
    assert os.environ.get("LINE_OUTBOUND_CHANNEL") is None
