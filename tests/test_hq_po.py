from datetime import date, datetime, timedelta, timezone

from src.handlers.hq_po_entry import is_hq_po_command
from src.handlers.services_menu import handle_services_menu, services_menu_handlers_match
from src.hq_po.docno import make_docno
from src.hq_po.group import group_by_vendor, sort_products
from src.hq_po.guards import (
    HqPoError,
    can_revert_row,
    can_stamp_row,
    chosen_pack,
    plan_cancel,
    plan_confirm,
    plan_created,
    receive_view,
)
from src.hq_po.insight import ai_recommendation, annotate_iclow_items, insight_only_lines
from src.hq_po.stock import parts9_order_qty
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


def test_ai_qty_subtracts_incoming():
    advice = ai_recommendation(_policy(), live_company=3, mtp2=1, incoming=6, now=NOW)
    assert advice is not None
    assert advice["ai_qty"] == 1
    assert "ค้างรับ 6" in advice["reason"]
    assert ai_recommendation(_policy(), live_company=3, mtp2=1, incoming=7, now=NOW) is None


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
    assert lines[0]["confirmable"] is True
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
    assert planned[0]["qty"] == 99
    fallback = plan_confirm(
        [{"iclow_id": 7}],
        {7: _live(iclow_id=7, qty=3, bcode="REAL")},
        vendor="V1",
    )
    assert fallback[0]["qty"] == 3
    try:
        plan_confirm([{"iclow_id": None}], {1: _live()}, vendor="V1")
    except HqPoError as exc:
        assert exc.code == "not_confirmable"
    else:
        raise AssertionError("expected not_confirmable")
    switched = plan_confirm(
        [{"iclow_id": 7, "vendor": "V2", "ui": "กล่อง", "mtp": 10}],
        {7: _live(iclow_id=7, vendor="V1", ui="ชิ้น")},
        vendor="V2",
    )
    assert switched[0]["vendor"] == "V2"
    assert switched[0]["ui"] == "กล่อง"
    assert switched[0]["mtp"] == 10
    same_unit = plan_confirm(
        [{"iclow_id": 7, "ui": "ชิ้น", "mtp": 1}],
        {7: _live(iclow_id=7, ui="ชิ้น")},
        vendor="V1",
    )
    assert same_unit[0]["mtp"] is None
    assert switched[0]["bcode"] == "A1"
    try:
        plan_confirm([{"iclow_id": 7}], {7: _live(iclow_id=7, vendor="V2")}, vendor="V1")
    except HqPoError as exc:
        assert exc.code == "vendor_mismatch"
    else:
        raise AssertionError("expected vendor_mismatch")


def test_plan_created_uses_server_line():
    resolved = {
        "B2": {
            "bcode": "B2",
            "vendor": "V9",
            "qty": 4,
            "descr": "from-server",
            "propose_meta": {"source": "insight", "ai_qty": 4, "reason": "gap"},
        }
    }
    planned = plan_created([{"bcode": "B2", "qty": 99}], resolved, vendor="V9")
    assert planned[0]["qty"] == 99
    fallback = plan_created([{"bcode": "B2"}], resolved, vendor="V9")
    assert fallback[0]["qty"] == 4
    assert planned[0]["iclow_id"] is None
    assert planned[0]["propose_meta"]["iclow_origin"] == "created"
    switched = plan_created([{"bcode": "B2", "vendor": "ALT", "qty": 2}], resolved, vendor="ALT")
    assert switched[0]["vendor"] == "ALT"
    try:
        plan_created([{"bcode": "B2"}], resolved, vendor="V1")
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


def test_parts9_order_qty_prefers_lot_then_min_gap():
    assert parts9_order_qty(qtyget=12, qtymin=4, qtyoh=1) == 12
    assert parts9_order_qty(qtyget=0, qtymin=10, qtyoh=3) == 7
    assert parts9_order_qty(qtyget=0, qtymin=2, qtyoh=5) is None
    assert parts9_order_qty(qtyget=8, qtymin=-1, qtyoh=0) is None


def test_page_defaults_product_view():
    html = page(user_name="Pannawit", stamp_enabled=False)
    assert 'id="viewProduct" class="on"' in html
    assert "ตามเจ้าหนี้" in html
    assert "ตามสินค้า" in html
    assert 'id="vendorSort"' in html
    assert 'id="sortCount" class="on"' in html
    assert "จำนวนสินค้า" in html
    assert "state.vendorSort" in html
    assert "data-key" in html
    assert "PARTS9" in html
    assert "ดูใบส่งเจ้าหนี้" in html
    assert "แบบย่อ" in html
    assert "แบบเต็ม" in html
    assert "คัดลอกส่งฝ่ายขาย" in html
    assert "/hq-po/api/sheet" in html
    assert "/hq-po/api/suppliers/" in html
    assert "HQ_PO_ICLOW_STAMP_ENABLED" in html
    assert "กำลังโหลดรายการรอสั่ง" in html
    assert "กำลังค้นหา" in html
    assert 'id="qStatus"' in html
    assert "ชื่อรุ่น" in html
    assert "เบอร์แท้" in html
    assert "เบอร์โรงงาน" in html
    assert "ยี่ห้อ" in html
    assert "ราคา " in html
    assert "ค่า " in html
    assert "เปลี่ยนเจ้าหนี้" in html
    assert "สั่งกับเจ้าหนี้นี้" in html
    assert "ดูสินค้าที่เคยสั่งจากเจ้าหนี้นี้" in html
    assert "เลือกเจ้าหนี้ใหม่" in html
    assert 'id="addProduct"' in html
    assert "เพิ่มสินค้าจากรหัสนี้" in html
    assert "เพิ่มสินค้าที่ไม่อยู่ในรายการ" in html
    assert "/hq-po/api/products" in html
    assert "/hq-po/api/vendors" in html
    assert "data-order" in html
    assert "สินค้าแทน" in html
    assert "data-peers" in html
    assert "data-open-vendor" in html
    assert "data-vendor-back" in html
    assert 'state.view === "vendor" && state.vendorKey != null' in html
    assert "row.bcode, row.descr" in html
    assert "row.vendor, row.vendor_name" in html
    assert "list_vendor" not in html
    assert "จะไปใบของ" not in html
    assert "hqpo-view" not in html
    assert "ยกเลิกบรรทัด" in html
    assert "data-cancel-line" in html
    assert 'id="orderVendor"' in html
    assert 'id="orderBcode"' in html
    assert "กรองเจ้าหนี้" in html
    assert "กรองรหัสสินค้า" in html
    assert "function orderVisible" in html
    assert "ไม่พบใบสั่งซื้อตามตัวกรอง" in html


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
    refreshed: list[bool] = []

    def dual_stock(codes, refresh=False):
        refreshed.append(refresh)
        return (
            {"A1": {"qtyoh2": 1, "mtp2": 1, "blocked": False, "descr": "bolt"}},
            {"A1": {"qtyoh2": 0, "mtp2": 1, "blocked": False}},
            True,
        )

    monkeypatch.setattr(suggest, "fetch_dual_stock", dual_stock)
    monkeypatch.setattr(
        suggest,
        "load_insight_policies_for",
        lambda codes: {code: _policy(bcode=code) for code in codes if code in {"A1", "B2"}},
    )
    monkeypatch.setattr(suggest, "fetch_incoming_qty", lambda: {})
    monkeypatch.setattr(suggest, "fetch_parts9_qty", lambda _codes: {})
    monkeypatch.setattr(suggest, "fetch_sheet_products", lambda _codes: {})

    def suppliers_must_wait(_codes):
        raise AssertionError("supplier scan must wait until one product asks")

    monkeypatch.setattr(suggest, "fetch_bcode_suppliers", suppliers_must_wait)
    monkeypatch.setattr(suggest, "_peek_insight_cache", lambda _key: None)

    def ensure(policies, bcodes, incoming=None):
        scanned.append(len([b for b in policies if b not in bcodes]))

    monkeypatch.setattr(suggest, "_ensure_insight_future", ensure)
    payload = suggest.build_suggest()
    assert payload["insight_pending"] is False
    assert "vendors" not in payload
    assert "suppliers" not in payload["items"][0]
    assert scanned == []
    assert [item["bcode"] for item in payload["items"]] == ["A1"]
    assert payload["items"][0]["source"] == "iclow"
    assert refreshed == [False]


def test_suggest_drops_a_line_with_no_product_code(monkeypatch):
    from src.hq_po import suggest

    rows = [
        {"iclow_id": 1, "vendor": "", "bcode": "", "descr": "", "mcode": "", "qty": 0, "ui": ""},
        {"iclow_id": 2, "vendor": "", "bcode": "-", "descr": "", "mcode": "", "qty": 0, "ui": ""},
        {"iclow_id": 7, "vendor": "V1", "bcode": "A1", "descr": "bolt", "mcode": "", "qty": 2, "ui": "PCS"},
    ]
    monkeypatch.setattr(suggest, "fetch_to_order_rows", lambda: rows)
    monkeypatch.setattr(suggest, "fetch_vendor_names", lambda _codes: {"V1": "Vendor"})
    monkeypatch.setattr(suggest, "fetch_dual_stock", lambda _codes, refresh=False: ({}, {}, False))
    monkeypatch.setattr(suggest, "fetch_incoming_qty", lambda: {})
    monkeypatch.setattr(suggest, "fetch_parts9_qty", lambda _codes: {})
    monkeypatch.setattr(suggest, "fetch_sheet_products", lambda _codes: {})
    payload = suggest.build_suggest()
    assert [item["bcode"] for item in payload["items"]] == ["A1"]


def test_suggest_attaches_model_codes_brand_price_and_cost(monkeypatch):
    from src.hq_po import suggest

    row = {
        "iclow_id": 7,
        "vendor": "V1",
        "bcode": "A1",
        "descr": "bolt",
        "mcode": "",
        "qty": 2,
        "ui": "PCS",
    }
    monkeypatch.setattr(suggest, "fetch_to_order_rows", lambda: [row])
    monkeypatch.setattr(suggest, "fetch_vendor_names", lambda _codes: {"V1": "Vendor"})
    monkeypatch.setattr(suggest, "fetch_dual_stock", lambda _codes, refresh=False: ({}, {}, False))
    monkeypatch.setattr(suggest, "load_insight_policies", lambda: {})
    monkeypatch.setattr(suggest, "fetch_parts9_qty", lambda _codes: {})
    monkeypatch.setattr(
        suggest,
        "fetch_sheet_products",
        lambda codes: {
            "A1": {
                "model": "Vios",
                "brand": "Toyota",
                "pcode": "OEM-1",
                "mcode": "FAC-1",
                "price1": 120,
                "costlast": 0,
                "costnet": 80.5,
            }
        }
        if "A1" in codes
        else {},
    )
    item = suggest.build_suggest()["items"][0]
    assert item["model"] == "Vios"
    assert item["pcode"] == "OEM-1"
    assert item["mcode"] == "FAC-1"
    assert item["brand"] == "Toyota"
    assert item["price"] == 120
    assert item["cost"] == 80.5


def test_suppliers_for_one_bcode(monkeypatch):
    from src.hq_po import suggest

    seen: list[list[str]] = []

    def fetch(codes):
        seen.append(list(codes))
        return (
            {"A1": [{"acctno": "NEW", "name": "ใหม่", "bills": 2, "last_date": "2026-10-01"}]},
            {"A1": {"acctno": "CAT", "name": "มาสเตอร์"}},
        )

    monkeypatch.setattr(suggest, "fetch_bcode_suppliers", fetch)
    rows = suggest.suppliers_for_bcode("A1", current="IC", current_name="บนแถว")
    assert seen == [["A1"]]
    assert rows[0]["acctno"] == "NEW"
    assert {row["acctno"] for row in rows} == {"NEW", "CAT", "IC"}


def test_supplier_choices_keep_purchase_accounts_and_the_current_vendor():
    from src.hq_po.iclow_read import supplier_choices

    rows = supplier_choices(
        [
            {"acctno": "OLD", "name": "เก่า", "bills": 1, "last_date": "2020-01-01"},
            {"acctno": "NEW", "name": "ใหม่", "bills": 4, "last_date": "2026-10-01"},
        ],
        current="IC",
        current_name="บนแถว",
        catalog="CAT",
        catalog_name="มาสเตอร์",
    )
    assert rows[0]["acctno"] == "NEW"
    assert {row["acctno"] for row in rows} == {"NEW", "OLD", "CAT", "IC"}
    assert rows[0]["name"] == "ใหม่"


def test_unknown_supplier_is_rejected(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(
        service,
        "fetch_bcode_suppliers",
        lambda _codes: (
            {"A1": [{"acctno": "NEW", "name": "ใหม่", "bills": 2, "last_date": "2026-01-01"}]},
            {"A1": {"acctno": "CAT", "name": "มาสเตอร์"}},
        ),
    )
    monkeypatch.setattr(service, "fetch_live_vendors", lambda _codes: {})
    service._assert_supplier_choices(
        [{"iclow_id": 7, "vendor": "NEW"}],
        live_by_id={7: {"bcode": "A1", "vendor": "OLD"}},
        resolved={},
    )
    service._assert_supplier_choices(
        [{"iclow_id": 7, "vendor": "CAT"}],
        live_by_id={7: {"bcode": "A1", "vendor": "OLD"}},
        resolved={},
    )
    try:
        service._assert_supplier_choices(
            [{"iclow_id": 7, "vendor": "NOPE"}],
            live_by_id={7: {"bcode": "A1", "vendor": "OLD"}},
            resolved={},
        )
    except HqPoError as exc:
        assert "ไม่เคยรับจาก" in str(exc)
    else:
        raise AssertionError("expected vendor_mismatch")


def test_live_ap_can_be_chosen_for_a_product_it_has_not_supplied(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(service, "fetch_bcode_suppliers", lambda _codes: ({}, {}))
    monkeypatch.setattr(service, "fetch_live_vendors", lambda codes: {"NEWAP": "ร้านใหม่"} if "NEWAP" in codes else {})
    service._assert_supplier_choices(
        [{"iclow_id": 7, "vendor": "NEWAP"}],
        live_by_id={7: {"bcode": "A1", "vendor": "OLD"}},
        resolved={},
    )


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


def test_chosen_pack_uses_small_unit_or_large_pack():
    product = {"ui": "ชิ้น", "ui2": "กล่อง", "mtp2": 10}
    assert chosen_pack("ชิ้น", product) == ("ชิ้น", 1.0)
    assert chosen_pack("กล่อง", product) == ("กล่อง", 10.0)
    assert chosen_pack("ลัง", product) is None
    assert chosen_pack("", product) is None
    assert chosen_pack("กล่อง", {"ui": "ชิ้น", "ui2": "กล่อง", "mtp2": 1}) is None


def test_peer_line_resolves_without_an_ai_policy(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(service, "fetch_unordered_bcodes", lambda _codes: set())
    monkeypatch.setattr(
        service,
        "fetch_sheet_products",
        lambda _codes: {"B2": {"descr": "seal", "ui": "ชิ้น", "ui2": "กล่อง", "mtp2": 10, "mcode": "M"}},
    )
    monkeypatch.setattr(
        service,
        "fetch_bcode_suppliers",
        lambda _codes: (
            {"B2": [{"acctno": "V2", "name": "ร้าน", "bills": 1, "last_date": "2026-01-01"}]},
            {},
        ),
    )
    resolved = service._resolve_peer(
        [{"bcode": "B2", "vendor": "V2", "ui": "กล่อง", "propose_meta": {"iclow_origin": "peer"}}]
    )
    assert resolved["B2"]["ui"] == "กล่อง"
    assert resolved["B2"]["propose_meta"]["iclow_origin"] == "created"
    monkeypatch.setattr(service, "fetch_unordered_bcodes", lambda _codes: {"B2"})
    try:
        service._resolve_peer([{"bcode": "B2", "vendor": "V2", "ui": "ชิ้น"}])
    except HqPoError as exc:
        assert exc.code == "already_on_iclow"
    else:
        raise AssertionError("expected already_on_iclow")


def test_peer_groups_keep_catalog_ahead_of_part_numbers():
    from src.hq_po.peers import group_peer_hits

    groups = group_peer_hits(
        catalog=[{"bcode": "B2", "descr": "confirmed"}],
        suggestions=[
            {"bcode": "B2", "source": "pcode", "sources": ["pcode"], "descr": "same oem"},
            {"bcode": "C3", "source": "pcode", "sources": ["pcode", "mcode"], "descr": "oem"},
            {"bcode": "D4", "source": "mcode", "sources": ["mcode"], "descr": "factory"},
            {"bcode": "E5", "source": "remarks", "sources": ["remarks"], "descr": "note"},
        ],
        pcode="OEM-1",
        mcode="FAC-1",
    )
    assert [group["key"] for group in groups] == ["catalog", "pcode", "mcode", "other"]
    assert groups[0]["label"] == "กลุ่มทดแทน"
    assert [line["bcode"] for line in groups[0]["lines"]] == ["B2"]
    assert groups[1]["label"] == "เบอร์แท้เดียวกัน OEM-1"
    assert [line["bcode"] for line in groups[1]["lines"]] == ["C3"]
    assert [line["bcode"] for line in groups[2]["lines"]] == ["D4"]
    assert [line["bcode"] for line in groups[3]["lines"]] == ["E5"]


def test_history_reorder_uses_the_peer_path():
    from src.hq_po.service import _peer_flag

    assert _peer_flag({"propose_meta": {"iclow_origin": "history"}})
    assert _peer_flag({"propose_meta": {"iclow_origin": "peer"}})
    assert _peer_flag({"propose_meta": {"iclow_origin": "catalog"}})
    assert not _peer_flag({"propose_meta": {"iclow_origin": "created"}})


def test_catalog_line_accepts_a_live_ap_without_purchase_history(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(service, "fetch_unordered_bcodes", lambda _codes: set())
    monkeypatch.setattr(
        service,
        "fetch_sheet_products",
        lambda _codes: {"C9": {"descr": "ใหม่", "ui": "ชิ้น", "mcode": "M"}},
    )
    monkeypatch.setattr(service, "fetch_bcode_suppliers", lambda _codes: ({}, {}))
    monkeypatch.setattr(service, "fetch_live_vendors", lambda codes: {"AP1": "เจ้าหนี้ใหม่"} if "AP1" in codes else {})
    resolved = service._resolve_peer(
        [{"bcode": "C9", "vendor": "AP1", "ui": "ชิ้น", "propose_meta": {"iclow_origin": "catalog"}}]
    )
    assert resolved["C9"]["vendor"] == "AP1"
    assert resolved["C9"]["propose_meta"]["catalog"] is True
    monkeypatch.setattr(service, "fetch_live_vendors", lambda _codes: {})
    try:
        service._resolve_peer(
            [{"bcode": "C9", "vendor": "GONE", "ui": "ชิ้น", "propose_meta": {"iclow_origin": "catalog"}}]
        )
    except HqPoError as exc:
        assert exc.code == "vendor_mismatch"
    else:
        raise AssertionError("expected vendor_mismatch")


def test_product_search_payload_marks_waiting_and_last_vendor(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(
        service,
        "search_products",
        lambda _q: [
            {
                "bcode": "01011980",
                "descr": "ลูกปืน",
                "model": "6203",
                "brand": "NSK",
                "pcode": "OEM",
                "mcode": "FAC",
                "ui": "ชิ้น",
                "ui2": "กล่อง",
                "mtp2": 10,
                "price1": 120,
                "costlast": 80,
                "costnet": 70,
                "vendor": "CAT",
                "qtyoh2": 4,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "fetch_bcode_suppliers",
        lambda _codes: (
            {"01011980": [{"acctno": "YSR", "name": "ยนต์เสรี", "bills": 3, "last_date": "2026-08-01"}]},
            {"01011980": {"acctno": "CAT", "name": "มาสเตอร์"}},
        ),
    )
    monkeypatch.setattr(service, "fetch_unordered_bcodes", lambda _codes: {"01011980"})
    monkeypatch.setattr(
        "src.hq_po.stock.fetch_dual_stock",
        lambda _codes, refresh=False: (
            {"01011980": {"qtyoh2": 2}},
            {"01011980": {"qtyoh2": 1}},
            True,
        ),
    )
    payload = service.product_search_payload("01011")
    item = payload["products"][0]
    assert item["bcode"] == "01011980"
    assert item["vendor"] == "YSR"
    assert item["last_vendor_name"] == "ยนต์เสรี"
    assert item["waiting"] is True
    assert item["company_qtyoh2"] == 3
    assert item["price"] == 120
    assert item["cost"] == 80


def test_product_search_skips_a_short_query():
    from src.hq_po.iclow_read import search_products

    assert search_products("a") == []
    assert search_products("  ") == []


def test_vendor_history_skips_products_already_waiting(monkeypatch):
    from src.hq_po import service

    monkeypatch.setattr(service, "fetch_vendor_names", lambda _codes: {"RR": "รุ่งโรจน์"})
    monkeypatch.setattr(
        service,
        "fetch_ordered_product_rows",
        lambda _acct: [
            {"bcode": "A1", "last_date": "2026-09-01", "bills": 2},
            {"bcode": "B2", "last_date": "2026-08-01", "bills": 1},
        ],
    )
    monkeypatch.setattr(service, "fetch_sheet_products", lambda _codes: {"B2": {"descr": "past", "ui": "ชิ้น"}})
    monkeypatch.setattr(service, "fetch_unordered_bcodes", lambda _codes: {"A1"})
    monkeypatch.setattr(
        "src.hq_po.stock.fetch_dual_stock",
        lambda _codes, refresh=False: ({"B2": {"qtyoh2": 1, "mtp2": 1}}, {"B2": {"qtyoh2": 0, "mtp2": 1}}, True),
    )
    monkeypatch.setattr("src.hq_po.stock.fetch_parts9_qty", lambda _codes: {})
    payload = service.vendor_ordered_payload("RR")
    assert [item["bcode"] for item in payload["items"]] == ["B2"]
    assert payload["items"][0]["propose_meta"]["iclow_origin"] == "history"
    assert payload["items"][0]["vendor"] == "RR"


def test_vendor_insight_refreshes_on_hand_before_the_gap(monkeypatch):
    from datetime import datetime, timezone

    from src.hq_po import service

    monkeypatch.setattr(service, "fetch_vendor_names", lambda _codes: {"JJY": "จ"})
    monkeypatch.setattr(
        service,
        "load_insight_policies_for_supplier",
        lambda *_args: {
            "13064261": {
                "bcode": "13064261",
                "last_supplier": "JJY",
                "safe_holding_qty": 4.91,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dead_stock": "no",
            }
        },
    )
    monkeypatch.setattr(service, "fetch_to_order_rows", lambda: [])
    monkeypatch.setattr(service, "fetch_incoming_qty", lambda: {})
    monkeypatch.setattr(service, "attach_catalog", lambda _lines: None)
    calls: list[bool] = []

    def fetch(_codes, refresh=False):
        calls.append(refresh)
        # Ledger on-hand already covers the target. Stored QTYOH2 would not.
        return (
            {"13064261": {"qtyoh2": 8, "mtp2": 1, "blocked": False, "descr": "seal"}},
            {"13064261": {"qtyoh2": 2, "mtp2": 1}},
            True,
        )

    monkeypatch.setattr("src.hq_po.stock.fetch_dual_stock", fetch)
    monkeypatch.setattr("src.hq_po.stock.fetch_parts9_qty", lambda _codes: {})
    payload = service.vendor_insight_payload("JJY")
    assert calls == [True]
    assert payload["items"] == []


def test_refresh_qtyoh2_syncs_both_sites(monkeypatch):
    import src.db.qtyoh2_ledger as ledger
    import src.parts9_explorer.db as explorer_db
    from src.hq_po.stock import fetch_dual_stock, refresh_qtyoh2

    monkeypatch.setattr(ledger, "qtyoh2_sync_on_read_enabled", lambda: True)
    engines = {"hq": object(), "syp": object()}
    monkeypatch.setattr(explorer_db, "get_site_writer_engine", lambda site: engines[site])
    seen: list[tuple[tuple[str, ...], object]] = []

    def sync(codes, *, engine):
        seen.append((tuple(codes), engine))
        return [type("Row", (), {"bcode": code, "skipped": False})() for code in codes]

    monkeypatch.setattr(ledger, "sync_qtyoh2_from_ledger_many", sync)
    from src.hq_po import stock as stock_mod

    stock_mod._fresh_until.clear()
    refresh_qtyoh2(["A1", "A1", " B2 "])
    assert {engine for _, engine in seen} == set(engines.values())
    assert {codes for codes, _ in seen} == {("A1", "B2")}
    seen.clear()
    refresh_qtyoh2(["A1", "B2"])
    assert seen == []

    seen.clear()
    monkeypatch.setattr(ledger, "qtyoh2_sync_on_read_enabled", lambda: False)
    refresh_qtyoh2(["A1"])
    assert seen == []

    order: list[str] = []
    monkeypatch.setattr(
        "src.hq_po.stock.refresh_qtyoh2",
        lambda codes, sites=("hq", "syp"): order.append("refresh"),
    )
    import src.transfer.parts9 as parts9

    monkeypatch.setattr(parts9, "_fetch_icmas_chunked", lambda site, codes: order.append(site) or {})
    fetch_dual_stock(["A1"], refresh=True)
    assert order[0] == "refresh"
    fetch_dual_stock(["A1"])
    assert order.count("refresh") == 1


def test_cancel_line_returns_the_row_to_iclow(monkeypatch):
    from src.hq_po import service

    class Settings:
        stamp_enabled = True

    order = {
        "order_id": "o1",
        "status": "ordered",
        "docno": "HP6910-AAAA",
        "lines": [
            {
                "line_id": "l1",
                "iclow_id": 9,
                "bcode": "A1",
                "canceled_at": None,
                "propose_meta": {"iclow_origin": "created"},
            },
            {
                "line_id": "l2",
                "iclow_id": 10,
                "bcode": "B2",
                "canceled_at": None,
            },
        ],
    }
    monkeypatch.setattr(service, "get_hq_po_settings", lambda: Settings())
    monkeypatch.setattr(service, "get_hq_po_supabase_client", lambda: object())
    monkeypatch.setattr(service, "get_order", lambda _client, _order_id: order)
    monkeypatch.setattr(
        service,
        "fetch_iclow_by_ids",
        lambda _ids: {
            9: {"iclow_id": 9, "bcode": "A1", "ordered": "Y", "received": "N", "docno": "HP6910-AAAA"}
        },
    )
    reverted: list[tuple[list, str]] = []
    marked: list[tuple] = []
    def _do_not_retire(*_args, **_kwargs):
        raise AssertionError("created row must return to ICLOW")

    monkeypatch.setattr(service, "revert_ordered", lambda lines, docno: reverted.append((lines, docno)))
    monkeypatch.setattr(service, "cancel_created", _do_not_retire)
    monkeypatch.setattr(
        service,
        "mark_line_canceled",
        lambda client, order_id, line_id, reason=None: marked.append((order_id, line_id, reason)),
    )
    service.cancel_order_line("o1", "l1")
    assert reverted[0][1] == "HP6910-AAAA"
    assert reverted[0][0][0]["iclow_id"] == 9
    assert marked == [("o1", "l1", "vendor_unavailable")]

    monkeypatch.setattr(
        service,
        "fetch_iclow_by_ids",
        lambda _ids: {
            9: {"iclow_id": 9, "bcode": "A1", "ordered": "Y", "received": "Y", "docno": "HP6910-AAAA"}
        },
    )
    try:
        service.cancel_order_line("o1", "l1")
    except HqPoError as exc:
        assert exc.code == "already_received"
    else:
        raise AssertionError("expected already_received")
