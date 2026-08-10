from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.stock_check.auth import mint_access_token, verify_access_token
from src.stock_check.daily_pick import (
    CandidateFlags,
    SalesSignals,
    _pick_from_group,
    abc_class,
    allocate_group_quotas,
    build_flags,
    is_abc_due,
    passes_repeat_gap,
    passes_restock_policy,
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


def test_lease_extend_keeps_alive_until_idle(tmp_path: Path):
    store = LocalStore(tmp_path / "t_idle.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=1000)
    store.claim_leases(
        session_id=sid,
        lease_items=[
            {
                "bcode": "C1",
                "pick_priority": 4,
                "pick_reasons": ["sold_yesterday"],
                "abc_class": "A",
                "sales_days_90": 40,
            }
        ],
        lease_ttl=300,
        now=1000,
    )
    # Near idle expiry — activity extends window
    assert store.extend_leases(sid, lease_ttl=300, now=1290) == 1
    assert store.expire_stale_leases(now=1300) == 0
    assert store.active_leased_bcodes() == {"C1"}
    # After extended window idle
    assert store.expire_stale_leases(now=1600) == 1
    assert store.active_leased_bcodes() == set()


def test_lease_persists_pick_pool_meta(tmp_path: Path):
    store = LocalStore(tmp_path / "t_meta.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=1000)
    store.claim_leases(
        session_id=sid,
        lease_items=[
            {
                "bcode": "D1",
                "pick_priority": 5,
                "pick_reasons": ["abc_due_B"],
                "abc_class": "B",
                "sales_days_90": 12,
            }
        ],
        lease_ttl=300,
        now=1000,
    )
    rows = store.list_leases_for_session(sid)
    assert len(rows) == 1
    assert rows[0]["pick_priority"] == 5
    assert "abc_due_B" in rows[0]["pick_reasons"]
    assert rows[0]["abc_class"] == "B"


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


def test_allocate_group_quotas_round_robin_routine_first():
    # Fill order: 4,5,6,1,2,3 — for N=10 → 4,5,6,1 get 2; 2,3 get 1
    q = allocate_group_quotas(10)
    assert q[4] == 2
    assert q[5] == 2
    assert q[6] == 2
    assert q[1] == 2
    assert q[2] == 1
    assert q[3] == 1
    assert sum(q.values()) == 10


def test_pick_from_group_prefers_nonblank_location():
    blank = ProductRow("B1", "blank", "", "", "", "", 1.0, "u", 1.0, "N")
    aisle = ProductRow("A1", "aisle", "", "", "A-01", "2", 1.0, "u", 1.0, "N")
    flags = CandidateFlags(sold_yesterday=True)
    pool = [
        ("", blank.bcode, blank, flags),
        ("A-01", aisle.bcode, aisle, flags),
    ]
    picked = _pick_from_group(pool, need=1, used=set(), prefer_loc="")
    assert len(picked) == 1
    assert picked[0][0].bcode == "A1"

    # Once walking an aisle, stay on it before blank bins.
    more = ProductRow("A2", "aisle2", "", "", "A-01", "", 1.0, "u", 1.0, "N")
    pool2 = [
        ("", blank.bcode, blank, flags),
        ("B-99", ProductRow("C1", "other", "", "", "B-99", "", 1.0, "u", 1.0, "N").bcode,
         ProductRow("C1", "other", "", "", "B-99", "", 1.0, "u", 1.0, "N"), flags),
        ("A-01", more.bcode, more, flags),
    ]
    picked2 = _pick_from_group(pool2, need=1, used=set(), prefer_loc="A-01")
    assert picked2[0][0].bcode == "A2"

def test_group_membership_negative_stays_risk_bucket():
    today = date(2026, 8, 11)
    product = ProductRow("X1", "neg", "", "", "L1", "", -2.0, "u", 1.0, "N")
    signals = SalesSignals(
        as_of=today,
        yesterday_bcodes=frozenset({"X1"}),
        sales_days_90={},
        sa_bcodes=frozenset(),
    )
    flags = build_flags(product=product, audit=None, signals=signals, today=today)
    assert flags.negative_or_anomaly is True
    assert flags.sold_yesterday is True
    # Membership for quotas still uses risk first so negatives don't steal routine slots
    assert flags.priority == 1


def test_group_membership_mismatch_beats_yesterday():
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


def test_qtymin_negative_skips_routine_keeps_risk():
    today = date(2026, 8, 11)
    signals = SalesSignals(
        as_of=today,
        yesterday_bcodes=frozenset({"Y1", "Y2"}),
        sales_days_90={"Y1": 40, "Y2": 0},
        sa_bcodes=frozenset({"Y3"}),
    )
    dead_sold = ProductRow(
        "Y1", "dead sold", "", "", "A1", "", 3.0, "u", 1.0, "N", qtymin=-1.0
    )
    dead_neg = ProductRow(
        "Y2", "dead neg", "", "", "A1", "", -2.0, "u", 1.0, "N", qtymin=-1.0
    )
    dead_sa = ProductRow(
        "Y3", "dead sa", "", "", "A1", "", 1.0, "u", 1.0, "N", qtymin=-1.0
    )
    live = ProductRow(
        "Y4", "live", "", "", "A1", "", 2.0, "u", 1.0, "N", qtymin=2.0
    )

    f_sold = build_flags(product=dead_sold, audit=None, signals=signals, today=today)
    f_neg = build_flags(product=dead_neg, audit=None, signals=signals, today=today)
    f_sa = build_flags(product=dead_sa, audit=None, signals=signals, today=today)
    f_live = build_flags(
        product=live,
        audit=None,
        signals=SalesSignals(
            as_of=today,
            yesterday_bcodes=frozenset({"Y4"}),
            sales_days_90={},
            sa_bcodes=frozenset(),
        ),
        today=today,
    )

    assert f_sold.priority == 4
    assert passes_restock_policy(dead_sold, f_sold) is False
    assert f_neg.priority == 1
    assert passes_restock_policy(dead_neg, f_neg) is True
    assert f_sa.priority == 3
    assert passes_restock_policy(dead_sa, f_sa) is True
    assert passes_restock_policy(live, f_live) is True


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
