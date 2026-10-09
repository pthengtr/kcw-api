from datetime import date, datetime, timedelta, timezone

from src.handlers.hq_po_entry import is_hq_po_command
from src.handlers.services_menu import handle_services_menu, services_menu_handlers_match
from src.hq_po.docno import make_docno
from src.hq_po.group import group_by_vendor, sort_products
from src.hq_po.guards import (
    HqPoError,
    can_revert_row,
    can_stamp_row,
    plan_cancel,
    plan_confirm,
    receive_view,
)
from src.hq_po.insight import ai_recommendation, annotate_iclow_items, insight_only_lines
from src.hq_po.ui import page


NOW = datetime(2026, 10, 9, 3, 0, tzinfo=timezone.utc)
FRESH = "2026-10-08T10:00:00+07:00"


def _policy(**kwargs):
    row = {
        "bcode": "A1",
        "generated_at": FRESH,
        "dead_stock": "no",
        "safe_holding_qty": 10,
        "safe_holding_reason": "",
        "suggested_order_qty": 12,
        "last_supplier": "V1",
    }
    row.update(kwargs)
    return row


def _live(**kwargs):
    row = {
        "iclow_id": 1,
        "vendor": "V1",
        "bcode": "A1",
        "descr": "bolt",
        "qty": 2,
        "ui": "PCS",
        "ordered": "N",
        "received": "N",
        "canceled": "N",
        "docno": "",
    }
    row.update(kwargs)
    return row


def test_docno_uses_buddhist_yymm():
    assert make_docno("a1b2c3d4", date(2026, 10, 9)) == "HP6910-A1B2"


def test_group_by_vendor_puts_blank_last_and_sorts_products():
    items = [
        {"vendor": "", "vendor_name": None, "bcode": "Z", "descr": "z", "confirmable": True, "iclow_id": 2},
        {"vendor": "V2", "vendor_name": "Beta", "bcode": "B", "descr": "b", "confirmable": True, "iclow_id": 3},
        {"vendor": "V1", "vendor_name": "Alpha", "bcode": "C", "descr": "c", "confirmable": True, "iclow_id": 5},
        {"vendor": "V1", "vendor_name": "Alpha", "bcode": "A", "descr": "a", "confirmable": True, "iclow_id": 4},
    ]
    groups = group_by_vendor(items)
    assert [g["vendor"] for g in groups] == ["V1", "V2", ""]
    assert [line["bcode"] for line in groups[0]["lines"]] == ["A", "C"]
    assert groups[0]["confirmable_count"] == 2


def test_product_sort_keeps_confirmable_before_insight():
    rows = sort_products(
        [
            {"bcode": "A", "descr": "a", "source": "insight", "confirmable": False, "iclow_id": None},
            {"bcode": "B", "descr": "b", "source": "iclow", "confirmable": True, "iclow_id": 1},
        ]
    )
    assert [row["bcode"] for row in rows] == ["B", "A"]


def test_ai_qty_is_company_gap_packed():
    advice = ai_recommendation(_policy(), live_company=3, mtp2=4, now=NOW)
    assert advice is not None
    assert advice["ai_qty"] == 8
    assert advice["reason"].startswith("คงเหลือ 3 / เป้า 10")


def test_ai_skips_stale_dead_enough_and_subunit():
    stale = (NOW - timedelta(days=30)).isoformat()
    assert ai_recommendation(_policy(generated_at=stale), live_company=0, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(dead_stock="yes"), live_company=0, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(), live_company=10, mtp2=1, now=NOW) is None
    assert ai_recommendation(
        _policy(safe_holding_qty=0.2, suggested_order_qty=0.4),
        live_company=0,
        mtp2=12,
        now=NOW,
    ) is None


def test_ai_falls_back_to_suggested_order_qty():
    advice = ai_recommendation(
        _policy(safe_holding_qty=None, suggested_order_qty=6),
        live_company=1,
        mtp2=1,
        now=NOW,
    )
    assert advice is not None
    assert advice["ai_qty"] == 5


def test_annotate_keeps_iclow_qty():
    items = [
        {
            "bcode": "A1",
            "source": "iclow",
            "qty": 2,
            "hq_qtyoh2": 1,
            "syp_qtyoh2": 1,
            "mtp2": 1,
            "hq_blocked": False,
        }
    ]
    annotate_iclow_items(items, {"A1": _policy()}, now=NOW)
    assert items[0]["qty"] == 2
    assert items[0]["propose_meta"]["source"] == "both"
    assert items[0]["propose_meta"]["ai_qty"] == 8


def test_insight_only_skips_iclow_and_blocked():
    policies = {
        "A1": _policy(bcode="A1"),
        "B2": _policy(bcode="B2", safe_holding_qty=6, last_supplier="V9"),
    }
    hq = {
        "A1": {"qtyoh2": 0, "blocked": False, "mtp2": 1, "descr": "A"},
        "B2": {"qtyoh2": 0, "blocked": False, "mtp2": 1, "descr": "B"},
    }
    syp = {
        "A1": {"qtyoh2": 0, "blocked": False, "mtp2": 1},
        "B2": {"qtyoh2": 0, "blocked": False, "mtp2": 1},
    }
    lines = insight_only_lines(policies, iclow_bcodes={"A1"}, hq_icmas=hq, syp_icmas=syp, now=NOW)
    assert [row["bcode"] for row in lines] == ["B2"]
    assert lines[0]["confirmable"] is False
    assert lines[0]["source"] == "insight"
    assert lines[0]["vendor"] == "V9"
    assert lines[0]["iclow_id"] is None


def test_stamp_and_revert_guards():
    assert can_stamp_row(_live()) is None
    assert can_stamp_row(_live(ordered="Y")) == "already_ordered"
    assert can_stamp_row(_live(received="Y")) == "already_received"
    assert can_stamp_row(_live(canceled="Y")) == "canceled"
    assert can_revert_row(_live(ordered="Y", docno="HP6910-A1B2"), "HP6910-A1B2") is None
    assert can_revert_row(_live(ordered="Y", docno="HP6910-A1B2", received="Y"), "HP6910-A1B2") == "already_received"
    assert can_revert_row(_live(ordered="Y", docno="PO6901-1"), "HP6910-A1B2") == "docno_mismatch"
    assert can_revert_row(_live(ordered="N", docno=""), "HP6910-A1B2") is None


def test_plan_confirm_uses_live_row_and_rejects_other_vendor():
    planned = plan_confirm(
        [{"iclow_id": 7, "bcode": "NOPE", "qty": 99, "propose_meta": {"source": "both", "ai_qty": 4}}],
        {7: _live(iclow_id=7, qty=3, bcode="REAL")},
        vendor="V1",
    )
    assert planned[0]["bcode"] == "REAL"
    assert planned[0]["qty"] == 3
    try:
        plan_confirm([{"iclow_id": None}], {1: _live()}, vendor="V1")
    except HqPoError as exc:
        assert exc.code == "not_confirmable"
    else:
        raise AssertionError("expected not_confirmable")
    try:
        plan_confirm([{"iclow_id": 7}], {7: _live(iclow_id=7, vendor="V2")}, vendor="V1")
    except HqPoError as exc:
        assert exc.code == "vendor_mismatch"
    else:
        raise AssertionError("expected vendor_mismatch")


def test_plan_cancel_blocks_received():
    try:
        plan_cancel([_live(docno="HP6910-A1B2", received="Y")], "HP6910-A1B2")
    except HqPoError as exc:
        assert exc.code == "already_received"
    else:
        raise AssertionError("expected already_received")


def test_receive_view_does_not_invent_a_write():
    view = receive_view(
        {"received": "Y", "rcvdno": "A1", "rcvddate": "2026-10-09"},
        {"pimas_matched_billno": "A1-99"},
    )
    assert view["label"] == "รับแล้ว"
    assert view["pimas_billno"] == "A1-99"
    assert receive_view({"received": "N"})["label"] == "ค้างรับ"


def test_page_defaults_vendor_view():
    html = page(user_name="Pannawit", stamp_enabled=False)
    assert "ตามเจ้าหนี้" in html
    assert "ตามสินค้า" in html
    assert "ไม่แตะ ICLOW" in html
    assert "HQ_PO_ICLOW_STAMP_ENABLED" in html
    assert "กำลังโหลดรายการรอสั่ง" in html


def test_suggest_returns_iclow_without_waiting_for_insight_scan(monkeypatch):
    from src.hq_po import suggest

    row = {
        "iclow_id": 7,
        "vendor": "V1",
        "bcode": "A1",
        "descr": "bolt",
        "mcode": "M",
        "qty": 2,
        "ui": "PCS",
    }
    scanned: list[int] = []

    monkeypatch.setattr(suggest, "fetch_to_order_rows", lambda: [row])
    monkeypatch.setattr(suggest, "fetch_vendor_names", lambda _codes: {"V1": "Vendor"})
    monkeypatch.setattr(
        suggest,
        "fetch_dual_stock",
        lambda codes: (
            {"A1": {"qtyoh2": 1, "mtp2": 1, "blocked": False, "descr": "bolt"}},
            {"A1": {"qtyoh2": 0, "mtp2": 1, "blocked": False}},
            True,
        ),
    )
    monkeypatch.setattr(
        suggest,
        "load_insight_policies",
        lambda: {"A1": _policy(), "B2": _policy(bcode="B2")},
    )
    monkeypatch.setattr(suggest, "_peek_insight_cache", lambda _key: None)

    def ensure(policies, bcodes):
        scanned.append(len([b for b in policies if b not in bcodes]))

    monkeypatch.setattr(suggest, "_ensure_insight_future", ensure)
    payload = suggest.build_suggest()
    assert payload["insight_pending"] is True
    assert scanned == [1]
    assert [item["bcode"] for item in payload["items"]] == ["A1"]
    assert payload["items"][0]["source"] == "iclow"


def test_line_command_and_menu():
    assert is_hq_po_command("สั่งซื้อ")
    assert is_hq_po_command("HQ PO")
    assert not is_hq_po_command("โอนสินค้า")
    labels = [
        c["action"]["label"]
        for c in handle_services_menu()["contents"]["body"]["contents"]
        if c.get("type") == "button"
    ]
    assert "สั่งซื้อ" in labels
    assert services_menu_handlers_match()["hq_po"]
