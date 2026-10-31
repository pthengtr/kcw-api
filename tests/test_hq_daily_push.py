import src.bot.line_bot as line_bot
from src.hq_daily_push import fail_names, format_hq_failure, log_excerpt, ok_names
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

    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "late-token")
    monkeypatch.setattr(line_bot.requests, "post", fake_post)
    line_bot.push_line_message("U1", "hi")
    assert captured["auth"] == "Bearer late-token"


def test_default_recipients(monkeypatch):
    monkeypatch.delenv("HQ_DAILY_PUSH_NAMES", raising=False)
    monkeypatch.delenv("HQ_DAILY_PUSH_FAIL_NAMES", raising=False)
    assert ok_names() == ["peung", "phu", "ice"]
    assert fail_names() == ["peung", "turbo"]


def test_failure_message_includes_step_and_log(tmp_path):
    log = tmp_path / "step.log"
    log.write_text("noise\nFAILED: vat inventory\n", encoding="utf-8")
    text = format_hq_failure("vat inventory", 1, log_excerpt(str(log)))
    assert text.startswith("HQ ประจำวันรันไม่สำเร็จ")
    assert "ขั้นตอน: vat inventory" in text
    assert "exit 1" in text
    assert "FAILED: vat inventory" in text
    assert "ยอดขาย" not in text
