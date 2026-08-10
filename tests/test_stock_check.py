from __future__ import annotations

import time
from pathlib import Path

from src.stock_check.auth import mint_access_token, verify_access_token
from src.stock_check.db_local import LocalStore
from src.stock_check.net import resolve_stock_check_public_base_url
from src.stock_check.parts9 import ProductRow, pick_top_products, score_product


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


def test_pick_prefers_never_audited():
    now = time.time()
    products = [
        ProductRow("1", "a", "", "", "L1", "", 5, "u", 1, "N"),
        ProductRow("2", "b", "", "", "L1", "", 5, "u", 1, "N"),
    ]
    audits = {"1": {"last_audited_at": now - 100}}
    score1 = score_product(products[0], last_audited_at=audits["1"]["last_audited_at"], now=now)
    score2 = score_product(products[1], last_audited_at=None, now=now)
    assert score2 > score1
    picked = pick_top_products(products, audits=audits, count=1, now=now)
    assert picked[0].bcode == "2"


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
