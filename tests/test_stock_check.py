from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.stock_check.auth import mint_access_token, verify_access_token
from src.stock_check.daily_pick import (
    CandidateFlags,
    SalesSignals,
    abc_class,
    build_flags,
    is_abc_due,
    passes_repeat_gap,
    within_repeat_gap,
)
from src.stock_check.db_local import LocalStore
from src.stock_check.net import resolve_stock_check_public_base_url
from src.stock_check.parts9 import ProductRow

BANGKOK = ZoneInfo("Asia/Bangkok")


def test_token_roundtrip():
    token = mint_access_token(
        secret="test-secret",
        line_user_id="U123",
        display_name="Tester",
        branch="HQ",
        ttl_seconds=60,
        now=1_700_000_000,
    )
    ident = verify_access_token(
        token,
        secret="test-secret",
        expected_branch="HQ",
        approver_ids={"U999"},
        now=1_700_000_010,
    )
    assert ident.line_user_id == "U123"
    assert ident.display_name == "Tester"
    assert ident.is_approver is False


def test_resolve_url_prefers_explicit(monkeypatch):
    monkeypatch.delenv("STOCK_CHECK_PUBLIC_BASE_URL", raising=False)
    url = resolve_stock_check_public_base_url(
        explicit="http://fixed.example:8787",
        port=8787,
    )
    assert url == "http://fixed.example:8787"


def test_resolve_url_autodetect(monkeypatch):
    monkeypatch.delenv("STOCK_CHECK_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("STOCK_CHECK_LISTEN_PORT", "8787")
    monkeypatch.setattr(
        "src.stock_check.net.detect_lan_ipv4",
        lambda: "192.168.1.50",
    )
    url = resolve_stock_check_public_base_url(explicit="", port=None)
    assert url == "http://192.168.1.50:8787"


def test_approver_flag():
    token = mint_access_token(
        secret="s",
        line_user_id="U999",
        display_name="Boss",
        branch="SYP",
        ttl_seconds=60,
        now=100,
    )
    ident = verify_access_token(
        token,
        secret="s",
        expected_branch="SYP",
        approver_ids={"U999"},
        now=110,
    )
    assert ident.is_approver is True


def test_lease_release_on_session_end(tmp_path: Path):
    store = LocalStore(tmp_path / "t.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=1000)
    claimed = store.claim_leases(session_id=sid, bcodes=["A1", "A2"], lease_ttl=100, now=1000)
    assert claimed == ["A1", "A2"]
    assert store.active_leased_bcodes() == {"A1", "A2"}
    n = store.end_session(sid, now=1010)
    assert n == 2
    assert store.active_leased_bcodes() == set()


def test_lease_ttl_expiry(tmp_path: Path):
    store = LocalStore(tmp_path / "t2.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=1000)
    store.claim_leases(session_id=sid, bcodes=["B1"], lease_ttl=10, now=1000)
    assert store.expire_stale_leases(now=1011) == 1
    assert store.active_leased_bcodes() == set()


def test_abc_class_thresholds():
    assert abc_class(0) == "N"
    assert abc_class(1) == "C"
    assert abc_class(9) == "C"
    assert abc_class(10) == "B"
    assert abc_class(29) == "B"
    assert abc_class(30) == "A"


def test_abc_due_cycles():
    today = date(2026, 8, 11)
    assert is_abc_due(klass="A", last_count=None, today=today) is True
    assert is_abc_due(klass="A", last_count=today - timedelta(days=20), today=today) is False
    assert is_abc_due(klass="A", last_count=today - timedelta(days=21), today=today) is True
    assert is_abc_due(klass="B", last_count=today - timedelta(days=44), today=today) is False
    assert is_abc_due(klass="B", last_count=today - timedelta(days=45), today=today) is True
    assert is_abc_due(klass="C", last_count=today - timedelta(days=90), today=today) is True
    assert is_abc_due(klass="N", last_count=None, today=today) is False


def test_repeat_gap_and_negative_override():
    today = date(2026, 8, 11)
    assert within_repeat_gap(today - timedelta(days=14), today) is True
    assert within_repeat_gap(today - timedelta(days=15), today) is False

    recent = CandidateFlags(
        last_count_date=today - timedelta(days=3),
        sold_yesterday=True,
        reasons=["sold_yesterday"],
    )
    assert passes_repeat_gap(recent, today) is False

    negative = CandidateFlags(
        negative_or_anomaly=True,
        last_count_date=today - timedelta(days=1),
        reasons=["negative_stock"],
    )
    assert passes_repeat_gap(negative, today) is True


def test_priority_prefers_negative_over_never():
    today = date(2026, 8, 11)
    product = ProductRow("X1", "neg", "", "", "L1", "", -2.0, "u", 1.0, "N")
    signals = SalesSignals(
        as_of=today,
        yesterday_bcodes=frozenset(),
        sales_days_90={},
        sa_bcodes=frozenset(),
    )
    flags = build_flags(product=product, audit=None, signals=signals, today=today)
    assert flags.negative_or_anomaly is True
    assert flags.never_counted is True
    assert flags.priority == 1
    assert "negative_stock" in flags.reasons


def test_priority_mismatch_beats_yesterday():
    today = date(2026, 8, 11)
    now = datetime(2026, 7, 1, tzinfo=BANGKOK).timestamp()
    product = ProductRow("X2", "m", "", "", "L1", "", 5.0, "u", 1.0, "N")
    signals = SalesSignals(
        as_of=today,
        yesterday_bcodes=frozenset({"X2"}),
        sales_days_90={"X2": 12},
        sa_bcodes=frozenset(),
    )
    flags = build_flags(
        product=product,
        audit={"last_audited_at": now, "last_outcome": "adjusted"},
        signals=signals,
        today=today,
    )
    assert flags.prior_mismatch is True
    assert flags.sold_yesterday is True
    assert flags.priority == 2


def test_stock_check_command_variants():
    from src.handlers.stock_check_entry import is_stock_check_command

    assert is_stock_check_command("เช็คสต็อก")
    assert is_stock_check_command("เช็กสตอก")
    assert is_stock_check_command("เช็คของ")
    assert is_stock_check_command("เช็ค สินค้า")
    assert is_stock_check_command("นับของ")
    assert is_stock_check_command("Check Stock")
    assert not is_stock_check_command("เช็คราคา")
    assert not is_stock_check_command("update")
