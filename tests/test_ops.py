from pathlib import Path

from src.access.helper import can_execute
from src.handlers.ops_entry import is_ops_command
from src.ops.iclow import ICLOW_STATUSES
from src.ops.net import rewrite_base_port
from src.ops.tf_prepare import (
    extract_po_docno,
    is_tf_transfer_bill,
    line_prepare_status,
    rollup_prepare_status,
)
from src.ops.ui import page
from src.parts9_explorer.query import parse_query

OPS_SPEC = Path(__file__).resolve().parents[1] / "scripts" / "line_rich_menu" / "menu_spec_ops.json"
STAFF_SPEC = Path(__file__).resolve().parents[1] / "scripts" / "line_rich_menu" / "menu_spec.json"


def test_ops_commands_use_existing_labels():
    assert is_ops_command("สถานะใบสั่งซื้อ")
    assert is_ops_command("ใบสั่งซื้อ")
    assert is_ops_command(" ใบสั่งซื้อ ")
    assert not is_ops_command("ทดลอง")
    assert not is_ops_command("เช็คสต็อก")
    assert not is_ops_command("ค้นหา")
    assert not is_ops_command("ภาพรวมยอดขาย")


def test_ops_command_does_not_steal_po_doc_search():
    parsed = parse_query("PO6905-392")
    assert parsed.doc_kind == "po"
    assert not is_ops_command("PO6905-392")


def test_ops_permission_admin_only():
    assert can_execute("admin", "สถานะใบสั่งซื้อ")
    assert can_execute("exec", "สถานะใบสั่งซื้อ")
    assert can_execute("staff", "สถานะใบสั่งซื้อ")
    assert not can_execute("user", "สถานะใบสั่งซื้อ")
    assert not can_execute("guest", "สถานะใบสั่งซื้อ")


def test_rewrite_explorer_port_to_ops():
    assert rewrite_base_port("http://100.113.143.97:8788", 8790) == "http://100.113.143.97:8790"
    assert rewrite_base_port("http://192.168.1.21:8788/", 8790) == "http://192.168.1.21:8790"
    assert rewrite_base_port("", 8790) is None


def test_ops_page_defaults_to_syp():
    html = page(user_name="ทดสอบ", site="", probes={"hq": {}, "syp": {}})
    assert 'let site = "syp";' in html
    assert 'data-site="syp"' in html
    assert 'data-site="hq"' in html
    html = page(
        user_name="ทดสอบ",
        site="syp",
        probes={"hq": {"ok": True}, "syp": {"ok": True}},
    )
    assert "จัดการ PO" in html
    assert "PO สาขา" in html
    assert "PO จัดซื้อ (HQ)" in html
    assert "รอสั่งซื้อ" in html
    assert "ค้างรับ" in html
    assert "รับบางส่วน" in html
    assert 'data-k="to_be_ordered"' in html
    assert ICLOW_STATUSES == ("to_be_ordered", "pending_receive", "partially_received")
    assert "สด" in html
    assert "จัดของบางส่วน" in html
    assert "จำนวนสั่ง" in html
    assert "จำนวน TF" in html
    assert 'id="dlgPo"' in html
    assert 'id="dlgAccount"' in html
    assert 'id="dlgPi"' in html
    assert "/ops/api/po/account/" in html
    assert "/ops/api/po/pi/" in html
    assert "พิมพ์ตาราง" in html
    assert "scrollIntoView" in html
    assert "@media print" in html
    assert "list-wrap" in html
    assert "showModal" in html
    assert "fmtQtyUi" in html
    assert "Math.round(n)" in html
    assert "productCell" in html
    assert "openAccount" in html
    assert "openPi" in html


def test_ops_page_hq_site_seed():
    html = page(user_name="x", site="hq", probes={"hq": {"ok": True}, "syp": {"ok": False}})
    assert 'let site = "hq";' in html
    assert "HQ SQL ok" in html
    assert "SYP SQL down" in html


def test_bill_key12_and_resolve_helpers():
    from src.ops.pi import bill_key12, resolve_pimas_batch

    assert bill_key12("  ABC1234567890XX  ") == "ABC123456789"
    assert bill_key12("") == ""
    # empty batch
    assert resolve_pimas_batch([]) == {}


def test_account_detail_empty_acctno():
    from src.ops.account import get_account_detail

    assert get_account_detail(acctno="") is None
    assert get_account_detail(acctno="   ") is None


def test_attach_hq_pimas_marks_missing(monkeypatch):
    from src.ops import iclow

    rows = [
        {"rcvdno": "A219623", "docno": "PO1"},
        {"rcvdno": "", "docno": "PO2"},
        {"rcvdno": "MISSING1", "docno": "PO3"},
    ]

    def fake_batch(rcvdnos):
        assert "A219623" in rcvdnos
        assert "MISSING1" in rcvdnos
        return {
            "A219623": {
                "pimas_matched_billno": "A219623",
                "pimas_match_method": "exact",
                "pimas_link_missing": False,
            },
            "MISSING1": {
                "pimas_matched_billno": None,
                "pimas_match_method": None,
                "pimas_link_missing": True,
            },
        }

    monkeypatch.setattr(iclow, "resolve_pimas_batch", fake_batch)
    iclow._attach_hq_pimas(rows)
    assert rows[0]["pimas_matched_billno"] == "A219623"
    assert rows[0]["pimas_match_method"] == "exact"
    assert rows[0]["pimas_link_missing"] is False
    assert rows[1]["pimas_link_missing"] is False
    assert rows[2]["pimas_link_missing"] is True


def test_syp_prepare_from_tf_remarks():
    assert extract_po_docno("1PO6908-054##0215560000262") == "1PO6908-054"
    assert extract_po_docno("no po here") is None
    assert is_tf_transfer_bill("TF6908-046")
    assert is_tf_transfer_bill("TFV6908-069")
    assert not is_tf_transfer_bill("TR6908-001")
    assert rollup_prepare_status(line_count=2, prepared_line_count=2, any_tf_line_count=2) == "prepared"
    assert rollup_prepare_status(line_count=2, prepared_line_count=1, any_tf_line_count=1) == "partially_prepared"
    assert rollup_prepare_status(line_count=2, prepared_line_count=0, any_tf_line_count=0) == "not_prepared"
    assert line_prepare_status(ordered_qty=4, tf_qty=4) == "prepared"
    assert line_prepare_status(ordered_qty=4, tf_qty=1) == "partially_prepared"
    assert line_prepare_status(ordered_qty=4, tf_qty=0) == "not_prepared"


def test_ops_rich_menu_is_separate_from_staff_default():
    import json

    staff = json.loads(STAFF_SPEC.read_text(encoding="utf-8"))
    ops = json.loads(OPS_SPEC.read_text(encoding="utf-8"))
    staff_texts = ["เช็คสต็อก", "ไทเกอร์", "ค้นหา", "สถานะใบสั่งซื้อ", "รูป", "ชำระเจ้าหนี้"]
    ops_texts = ["เช็คสต็อก", "ไทเกอร์", "ค้นหา", "สถานะใบสั่งซื้อ", "รูป", "ชำระเจ้าหนี้"]
    assert [a["action"]["text"] for a in staff["areas"]] == staff_texts
    assert [a["action"]["text"] for a in ops["areas"]] == ops_texts
    assert ops["areas"][3]["action"]["label"] == "PO โอนสินค้า"
    assert ops["areas"][5]["action"]["label"] == "ชำระเจ้าหนี้"
    assert staff["size"] == {"width": 2500, "height": 1686}
    assert ops["size"] == {"width": 2500, "height": 1686}
    assert staff["name"] != ops["name"]
