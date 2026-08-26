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
    assert '<option value="syp" selected>' in html
    assert '<option value="hq" selected>' not in html
    html = page(
        user_name="ทดสอบ",
        site="syp",
        probes={"hq": {"ok": True}, "syp": {"ok": True}},
    )
    assert "ใบสั่งซื้อ" in html
    assert "รอสั่งซื้อ" in html
    assert "ค้างรับ" in html
    assert "รับบางส่วน" in html
    assert 'data-k="to_be_ordered"' in html
    assert ICLOW_STATUSES == ("to_be_ordered", "pending_receive", "partially_received")
    assert 'value="syp" selected' in html or 'value="syp"  selected' in html or 'option value="syp" selected' in html
    assert "สด" in html
    assert "จัดของบางส่วน" in html
    assert "จำนวนสั่ง" in html
    assert "จำนวน TF" in html
    assert 'id="dlg"' in html
    assert "showModal" in html
    assert "scrollIntoView" not in html
    assert "fmtQtyUi" in html
    assert "Math.round(n)" in html


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
    staff_texts = ["เช็คสต็อก", "ไทเกอร์", "ค้นหา", "สถานะใบสั่งซื้อ", "รูป", "วิธีใช้"]
    ops_texts = ["เช็คสต็อก", "ไทเกอร์", "ค้นหา", "สถานะใบสั่งซื้อ", "รูป", "วิธีใช้"]
    assert [a["action"]["text"] for a in staff["areas"]] == staff_texts
    assert [a["action"]["text"] for a in ops["areas"]] == ops_texts
    assert ops["areas"][3]["action"]["label"] == "PO โอนสินค้า"
    assert ops["areas"][5]["action"]["label"] == "วิธีใช้ Bot"
    assert staff["size"] == {"width": 2500, "height": 1686}
    assert ops["size"] == {"width": 2500, "height": 1686}
    assert staff["name"] != ops["name"]
