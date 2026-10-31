from datetime import date
from decimal import Decimal

import pytest

from src.handlers.router import route_user_text
from src.handlers.tar_transfer import handle_tar_transfer_command
from src.handlers.transfer_entry import is_transfer_command
from src.tar_transfer.push import already_sent, mark_sent, push_recipient_ids
from src.tar_transfer.summary import (
    command_date,
    format_tar_transfer_message,
    is_tar_transfer_command,
    load_tar_transfer,
    parse_user_date,
)


class _Result:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row

    def fetchall(self):
        return self._row


class _Connection:
    def __init__(self, row):
        self._row = row
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        self.params = params
        return _Result(self._row)


class _Engine:
    def __init__(self, row):
        self.connection = _Connection(row)

    def connect(self):
        return self.connection


def _row(*, latest=date(2026, 10, 30)):
    return (
        Decimal("146140"),
        4,
        Decimal("-3610"),
        2,
        Decimal("43713"),
        3,
        Decimal("-1690"),
        1,
        latest,
    )


def test_command_shapes():
    assert is_tar_transfer_command("โอนtar")
    assert is_tar_transfer_command("โอน TAR")
    assert is_tar_transfer_command("โอนtar 2026-10-30")
    assert not is_tar_transfer_command("โอน")
    assert not is_tar_transfer_command("โอนสินค้า")
    assert not is_transfer_command("โอนtar")
    assert is_transfer_command("โอน")


def test_date_formats():
    today = date(2026, 10, 31)
    assert command_date("โอนtar", today=today) == date(2026, 10, 30)
    assert parse_user_date("2026-10-30", today=today) == date(2026, 10, 30)
    assert parse_user_date("30/10/2026", today=today) == date(2026, 10, 30)
    assert parse_user_date("30/10/2569", today=today) == date(2026, 10, 30)
    assert parse_user_date("30/10/69", today=today) == date(2026, 10, 30)
    assert command_date("โอนtar 30-10-2026", today=today) == date(2026, 10, 30)
    with pytest.raises(ValueError):
        parse_user_date("เมื่อวาน", today=today)


def test_net_is_tar_plus_negative_cntar():
    engine = _Engine(_row())
    summary = load_tar_transfer(engine, date(2026, 10, 30))
    assert summary["ready"] is True
    assert summary["hq_net"] == Decimal("142530")
    assert summary["syp_net"] == Decimal("42023")
    assert engine.connection.params == {"d": date(2026, 10, 30)}
    text = format_tar_transfer_message(summary)
    assert "TAR-CNTAR: 142,530.00" in text
    assert "3TAR-3CNTAR: 42,023.00" in text


def test_missing_day_says_latest():
    engine = _Engine(
        (0, 0, 0, 0, 0, 0, 0, 0, date(2026, 10, 30))
    )
    summary = load_tar_transfer(engine, date(2026, 10, 31))
    assert summary["ready"] is False
    text = format_tar_transfer_message(summary)
    assert "2026-10-31" in text
    assert "ข้อมูลล่าสุดถึงวันที่ 2026-10-30" in text


def test_route_admin_command(monkeypatch):
    monkeypatch.setattr(
        "src.tar_transfer.summary.bangkok_today",
        lambda now=None: date(2026, 10, 31),
    )
    engine = _Engine(_row())
    result = route_user_text(
        engine,
        "โอนtar",
        {"access_group": "admin", "line_user_id": "Uadmin"},
    )
    assert result["text"].startswith("โอน TAR วันที่ 2026-10-30")
    assert engine.connection.params == {"d": date(2026, 10, 30)}


def test_route_denies_other_users(monkeypatch):
    monkeypatch.setattr(
        "src.handlers.tar_transfer.push_recipient_ids",
        lambda engine: [],
    )
    result = handle_tar_transfer_command(
        _Engine(_row()),
        "โอนtar 2026-10-30",
        {"access_group": "user", "line_user_id": "Ustaff"},
    )
    assert result["text"] == "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"


def test_push_recipient_matches_display_name(monkeypatch):
    monkeypatch.delenv("TAR_TRANSFER_PUSH_LINE_USER_ID", raising=False)
    monkeypatch.setenv("TAR_TRANSFER_PUSH_NAMES", "narumonwit")
    engine = _Engine(
        [
            ("Uother", "Nu"),
            ("Unaru", "Narumon Wit"),
        ]
    )
    assert push_recipient_ids(engine) == ["Unaru"]


def test_push_state_skips_same_day(tmp_path):
    path = tmp_path / "sent"
    day = date(2026, 10, 31)
    assert already_sent(day, path) is False
    mark_sent(day, path)
    assert already_sent(day, path) is True
    assert already_sent(date(2026, 10, 30), path) is False
