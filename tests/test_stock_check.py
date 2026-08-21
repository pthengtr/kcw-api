from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

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
        now=1_700_000_010,
    )
    assert ident.line_user_id == "U123"
    assert ident.display_name == "Tester"


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


def _sample_product(bcode: str = "P1", qty: float = 10.0) -> ProductRow:
    return ProductRow(
        bcode,
        "sample",
        "",
        "",
        "A-01",
        "",
        qty,
        "u",
        1.0,
        "N",
    )


def test_pending_draft_lookup(tmp_path: Path):
    store = LocalStore(tmp_path / "pending.sqlite3")
    assert store.get_pending_draft_for_bcode("P1") is None
    assert store.pending_bcodes() == set()
    store.create_draft(
        {
            "bcode": "P1",
            "descr": "x",
            "location1": "",
            "location2": "",
            "system_qty": 5.0,
            "counted_qty": 3.0,
            "variance": -2.0,
            "entry_mode": "total",
            "source": "ondemand",
            "status": "pending",
            "operator_line_user_id": "U1",
            "operator_name": "A",
            "notes": None,
            "completed_at": None,
        }
    )
    assert store.pending_bcodes() == {"P1"}
    row = store.get_pending_draft_for_bcode("P1")
    assert row is not None
    assert row["operator_name"] == "A"


def test_submit_blocked_when_pending_draft(tmp_path: Path, monkeypatch):
    from src.stock_check.service import StockCheckService

    store = LocalStore(tmp_path / "block_pending.sqlite3")
    sid = store.create_session(line_user_id="U2", display_name="B", is_approver=False, now=1000)
    store.create_draft(
        {
            "bcode": "P1",
            "descr": "x",
            "location1": "",
            "location2": "",
            "system_qty": 5.0,
            "counted_qty": 3.0,
            "variance": -2.0,
            "entry_mode": "total",
            "source": "batch",
            "status": "pending",
            "operator_line_user_id": "U1",
            "operator_name": "A",
            "notes": None,
            "completed_at": None,
        }
    )
    product = _sample_product()
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: product if bcode == "P1" else None,
    )
    svc = StockCheckService(store=store)
    session = store.get_session(sid)
    with pytest.raises(ValueError, match="รออนุมัติ"):
        svc.submit_count(session=session, bcode="P1", difference=-1.0)


def test_submit_blocked_when_leased_elsewhere(tmp_path: Path, monkeypatch):
    from src.stock_check.service import StockCheckService

    now = time.time()
    store = LocalStore(tmp_path / "block_lease.sqlite3")
    sid_a = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=now)
    sid_b = store.create_session(line_user_id="U2", display_name="B", is_approver=False, now=now)
    store.claim_leases(session_id=sid_a, bcodes=["P1"], lease_ttl=300, now=now)
    product = _sample_product()
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: product if bcode == "P1" else None,
    )
    svc = StockCheckService(store=store)
    session_b = store.get_session(sid_b)
    with pytest.raises(ValueError, match="คนอื่น"):
        svc.submit_count(session=session_b, bcode="P1", difference=-1.0)


def test_submit_allowed_for_lease_holder(tmp_path: Path, monkeypatch):
    from src.stock_check.service import StockCheckService

    now = time.time()
    store = LocalStore(tmp_path / "allow_lease.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=now)
    store.claim_leases(session_id=sid, bcodes=["P1"], lease_ttl=300, now=now)
    product = _sample_product()
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: product if bcode == "P1" else None,
    )
    svc = StockCheckService(store=store)
    session = store.get_session(sid)
    result = svc.submit_count(session=session, bcode="P1", difference=-1.0)
    assert result["status"] == "pending"
    assert store.get_pending_draft_for_bcode("P1") is not None


def test_submission_flags_on_product_detail(tmp_path: Path, monkeypatch):
    from src.stock_check.service import StockCheckService

    now = time.time()
    store = LocalStore(tmp_path / "flags.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="A", is_approver=False, now=now)
    store.claim_leases(session_id=sid, bcodes=["P1"], lease_ttl=300, now=now)
    product = _sample_product()
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: product if bcode == "P1" else None,
    )
    svc = StockCheckService(store=store)
    card = svc.product_detail("P1", session_id=sid)
    assert card["submit_blocked"] is False

    sid_b = store.create_session(line_user_id="U2", display_name="B", is_approver=False, now=now + 1)
    card_b = svc.product_detail("P1", session_id=sid_b)
    assert card_b["leased_elsewhere"] is True
    assert card_b["submit_blocked"] is True


def _pending_draft(**overrides):
    base = {
        "bcode": "P1",
        "descr": "Test",
        "location1": "A1",
        "location2": "",
        "system_qty": 10.0,
        "counted_qty": 8.0,
        "variance": -2.0,
        "entry_mode": "total",
        "source": "batch",
        "status": "pending",
        "operator_line_user_id": "U1",
        "operator_name": "Alice",
        "notes": None,
        "completed_at": None,
    }
    base.update(overrides)
    return base


def test_self_approve_blocked(tmp_path: Path):
    from src.stock_check.service import StockCheckService

    store = LocalStore(tmp_path / "mc.sqlite3")
    draft_id = store.create_draft(_pending_draft())
    svc = StockCheckService(store=store)
    session = {"line_user_id": "U1", "display_name": "Alice", "id": "s1"}
    with pytest.raises(PermissionError, match="own draft"):
        svc.approve_draft(draft_id=draft_id, approver_session=session)


def test_cross_user_approve_allowed(tmp_path: Path, monkeypatch):
    from src.stock_check.parts9 import ProductRow
    from src.stock_check.service import StockCheckService

    store = LocalStore(tmp_path / "mc2.sqlite3")
    draft_id = store.create_draft(_pending_draft())
    svc = StockCheckService(store=store)
    product = ProductRow(
        bcode="P1",
        descr="Test",
        pcode="",
        mcode="",
        location1="A1",
        location2="",
        qtyoh2=10.0,
        ui1="",
        mtp2=1.0,
        canceled="N",
    )

    class _Posted:
        billno = "SA001"
        new_qtyoh2 = 8.0

    monkeypatch.setattr("src.stock_check.service.get_product_by_bcode", lambda bcode: product)
    monkeypatch.setattr(
        "src.stock_check.service.post_stock_adjustment",
        lambda **kwargs: _Posted(),
    )
    checker = {"line_user_id": "U2", "display_name": "Bob", "id": "s2"}
    result = svc.approve_draft(draft_id=draft_id, approver_session=checker)
    assert result["ok"] is True
    assert result["status"] == "posted"


def test_owner_can_edit_pending_draft(tmp_path: Path, monkeypatch):
    from src.stock_check.parts9 import ProductRow
    from src.stock_check.service import StockCheckService

    store = LocalStore(tmp_path / "edit.sqlite3")
    draft_id = store.create_draft(_pending_draft())
    svc = StockCheckService(store=store)
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: ProductRow(
            bcode="P1",
            descr="Test",
            pcode="",
            mcode="",
            location1="A1",
            location2="",
            qtyoh2=9.0,
            ui1="",
            mtp2=1.0,
            canceled="N",
        ),
    )
    owner = {"line_user_id": "U1", "display_name": "Alice", "id": "s1"}
    result = svc.edit_pending_draft(
        draft_id=draft_id,
        session=owner,
        counted_qty=7.0,
    )
    assert result["counted_qty"] == 7.0
    assert result["variance"] == pytest.approx(-2.0)
    updated = store.get_draft(draft_id)
    assert updated["edit_count"] == 1


def test_work_events_recorded(tmp_path: Path, monkeypatch):
    from src.stock_check.parts9 import ProductRow
    from src.stock_check.service import StockCheckService

    store = LocalStore(tmp_path / "work.sqlite3")
    sid = store.create_session(line_user_id="U1", display_name="Alice", is_approver=False, now=1000)
    svc = StockCheckService(store=store)
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: ProductRow(
            bcode="P1",
            descr="Test",
            pcode="",
            mcode="",
            location1="A1",
            location2="",
            qtyoh2=10.0,
            ui1="",
            mtp2=1.0,
            canceled="N",
        ),
    )
    session = {"line_user_id": "U1", "display_name": "Alice", "id": sid}
    svc.submit_count(session=session, bcode="P1", counted_qty=8.0)
    summary = store.summarize_work_events(line_user_id="U1", since_ts=0)
    assert summary.get("count_variance") == 1


def test_drift_redirects_to_review(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.routers import stock_check as sc_router
    from app.stock_check_app import app
    from src.stock_check.parts9 import ProductRow
    from src.stock_check.service import StockCheckService

    data_dir = tmp_path / "drift"
    monkeypatch.setenv("STOCK_CHECK_ENABLED", "true")
    monkeypatch.setenv("STOCK_CHECK_BRANCH", "HQ")
    monkeypatch.setenv("STOCK_CHECK_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("STOCK_CHECK_DATA_DIR", str(data_dir))

    store = LocalStore(data_dir / "stock_check.sqlite3")
    draft_id = store.create_draft(_pending_draft(operator_line_user_id="U1"))
    checker_sid = store.create_session(line_user_id="U2", display_name="Bob", is_approver=False, now=1000)
    monkeypatch.setattr(sc_router, "_service", lambda: StockCheckService(store=store))
    monkeypatch.setattr(
        "src.stock_check.service.get_product_by_bcode",
        lambda bcode: ProductRow(
            bcode="P1",
            descr="Test",
            pcode="",
            mcode="",
            location1="A1",
            location2="",
            qtyoh2=7.0,
            ui1="",
            mtp2=1.0,
            canceled="N",
        ),
    )

    client = TestClient(app)
    client.cookies.set(sc_router.SESSION_COOKIE, checker_sid)
    resp = client.post(f"/stock-check/approve/{draft_id}", follow_redirects=False)
    assert resp.status_code == 303
    assert f"/stock-check/approve/{draft_id}/review" in resp.headers["location"]


def test_sa_writer_always_posts_mtp_one_for_pack_skus():
    """SIDET.MTP must be 1 even when ICMAS.MTP2 is a large pack factor."""
    from unittest.mock import MagicMock

    from src.stock_check.config import StockCheckSettings
    from src.stock_check.sa_writer import post_stock_adjustment

    product = ProductRow(
        bcode="15010490",
        descr="bearing",
        pcode="P",
        mcode="M",
        location1="A1",
        location2="",
        qtyoh2=13.0,
        ui1="หน่วย",
        mtp2=80.0,
        canceled="N",
    )
    settings = StockCheckSettings.model_construct(
        stock_check_branch="HQ",
        pos_mssql_writer_username="writer",
        pos_mssql_writer_password="x",
    )

    captured: list[dict] = []

    def _execute(sql, params=None):
        sql_s = str(sql)
        captured.append({"sql": sql_s, "params": dict(params or {})})
        result = MagicMock()
        if "MAX(BILLNO)" in sql_s:
            result.mappings.return_value.first.return_value = {"max_no": None}
        elif "SELECT QTYOH2" in sql_s:
            result.mappings.return_value.first.return_value = {"QTYOH2": 13.0}
        else:
            result.mappings.return_value.first.return_value = None
        return result

    conn = MagicMock()
    conn.execute.side_effect = _execute
    eng = MagicMock()
    eng.begin.return_value.__enter__.return_value = conn
    eng.begin.return_value.__exit__.return_value = None

    posted = post_stock_adjustment(
        settings=settings,
        product=product,
        variance=-3.0,
        operator_name="Tester",
        approver_name="Approver",
        engine=eng,
    )
    assert posted.billtype == "1"
    assert posted.qty_signed == 3.0
    assert posted.new_qtyoh2 == 10.0

    sidet = next(c for c in captured if "INSERT INTO dbo.SIDET" in c["sql"])
    assert sidet["params"]["mtp"] == 1.0
    assert sidet["params"]["ui"] == "หน่วย"
    assert sidet["params"]["qty"] == 3.0


def test_product_row_includes_model():
    product = ProductRow(
        bcode="P1",
        descr="bearing",
        pcode="P",
        mcode="M",
        location1="A1",
        location2="",
        qtyoh2=3.0,
        ui1="u",
        mtp2=1.0,
        canceled="N",
        model="1LT",
    )
    assert product.as_dict()["model"] == "1LT"


def test_product_card_and_info_show_model():
    from src.stock_check.ui import _product_card_html, product_page

    item = {
        "bcode": "P1",
        "descr": "bearing",
        "model": "1LT",
        "location1": "A-01",
        "location2": "",
        "qtyoh2": 4,
        "last_audited_at": None,
    }
    card = _product_card_html(item, href="/stock-check/product/P1")
    assert "รุ่น 1LT" in card
    info = product_page(user={"display_name": "T", "line_user_id": "U1"}, item=item)
    assert "รุ่น 1LT" in info
    blank = _product_card_html({**item, "model": ""}, href="/x")
    assert "รุ่น" not in blank
