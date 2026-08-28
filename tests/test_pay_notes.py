from src.handlers.pay_notes_entry import is_pay_notes_command
from src.pay_notes.net import rewrite_base_port
from src.pay_notes.ui import initials, page
from src.pay_notes.writer import PayNoteWriteError, create_pay_note
from src.pay_notes.config import PayNotesSettings
from src.pay_notes.parts9 import attach_pidet_lines, infer_settle_method
from src.pay_notes.baht_text import baht_text
from app.routers.pay_notes import _note_totals, _workflow_meta


def test_pay_notes_commands():
    assert is_pay_notes_command("ชำระเจ้าหนี้")
    assert is_pay_notes_command("โน้ตจ่าย")
    assert is_pay_notes_command(" โน้ต ")
    assert is_pay_notes_command("paynote")
    assert not is_pay_notes_command("ค้นหา")


def test_rewrite_explorer_port_to_pay_notes():
    assert rewrite_base_port("http://100.113.143.97:8788", 8791) == "http://100.113.143.97:8791"
    assert rewrite_base_port("", 8791) is None


def test_pay_notes_page_renders():
    html = page(user_name="ทดสอบ", site="HQ", write_enabled=False)
    assert "ชำระเจ้าหนี้" in html
    assert "ทดสอบ" in html
    assert "WRITE_ENABLED = false" in html
    assert "สร้างใบวางบิล" in html
    assert "รอชำระ" in html
    assert "ใบสำคัญจ่าย" in html
    assert "รอแนบหลักฐาน" in html
    assert "ค้นหาตามเจ้าหนี้" in html
    assert "themeBtn" in html
    assert "kcw.pay_notes.theme" in html
    assert 'id="tabCreate"' in html
    assert 'id="tabPending"' in html
    assert 'id="tabAwaitProof"' in html
    assert 'id="tabVoucher"' in html
    assert 'id="tabByAp"' in html
    assert 'id="tabNotes"' not in html
    assert 'id="tabVouchers"' not in html
    assert 'id="panelEdit"' in html
    assert 'mob-cards' in html
    assert 'id="btnPrintDetail"' in html
    assert 'id="detBills"' in html
    assert 'id="printSheet"' in html
    assert "รายละเอียดบิลซื้อ" in html
    assert "ใบสำคัญจ่าย / PAYMENT VOUCHER" in html


def test_page_has_voucher_and_proof_tabs():
    html = page(user_name="Alice Doe", site="HQ", write_enabled=True)
    assert "ใบสำคัญจ่าย" in html
    assert "บันทึกการจ่าย" in html
    assert "WRITE_ENABLED = true" in html
    assert "/vouchers" in html
    assert "/vouchered" in html
    assert "openEditNote" in html
    assert "data-print=" in html
    assert "openDetailByKey" in html
    assert "AD" in html


def test_workflow_meta():
    pending = _workflow_meta()
    assert pending["stage"] == "pending"
    assert pending["is_editable"] is True
    await_proof = _workflow_meta(voucno="KCPN6908-001", has_proof=False)
    assert await_proof["stage"] == "await_proof"
    assert await_proof["is_editable"] is False
    done = _workflow_meta(voucno="KCPN6908-001", has_proof=True)
    assert done["stage"] == "voucher"
    assert done["is_editable"] is False


def test_ui_initials():
    assert initials("Alice Doe") == "AD"
    assert initials("peung") == "PE"
    assert initials("ทดสอบ") == "ทด"
    assert initials("") == "OP"


def test_infer_settle_method():
    assert infer_settle_method("โอน") == "transfer"
    assert infer_settle_method("") == "cash"
    assert infer_settle_method(None) == "cash"
    assert infer_settle_method("123456") == "cheque"


def test_create_pay_note_write_disabled():
    settings = PayNotesSettings(pay_notes_write_enabled=False)
    try:
        create_pay_note(
            settings=settings,
            acctno="7GP",
            acctname="Test Vendor",
            noteno="TEST-NOTE-001",
            billnos=["B1"],
        )
        raised = False
    except PayNoteWriteError as exc:
        raised = True
        assert exc.code == "write_disabled"
    assert raised


def test_noteno_max_length_validation_in_writer():
    settings = PayNotesSettings(pay_notes_write_enabled=True, pos_mssql_writer_username="x")
    try:
        create_pay_note(
            settings=settings,
            acctno="7GP",
            acctname="Test",
            noteno="X" * 16,
            billnos=["B1"],
        )
        raised = False
    except PayNoteWriteError as exc:
        raised = True
        assert exc.code == "validation"
    assert raised


def test_cancel_pay_note_write_disabled():
    settings = PayNotesSettings(pay_notes_write_enabled=False)
    try:
        from src.pay_notes.writer import cancel_unvouchered_pay_note

        cancel_unvouchered_pay_note(settings=settings, acctno="7GP", noteno="X")
        raised = False
    except PayNoteWriteError as exc:
        raised = True
        assert exc.code == "write_disabled"
    assert raised


def test_baht_text_matches_voucher_sample():
    assert baht_text(18454.25) == "หนึ่งหมื่นแปดพันสี่ร้อยห้าสิบสี่บาทยี่สิบห้าสตางค์"
    assert baht_text(1) == "หนึ่งบาทถ้วน"
    assert baht_text(21) == "ยี่สิบเอ็ดบาทถ้วน"
    assert baht_text(11) == "สิบเอ็ดบาทถ้วน"
    assert baht_text(0.25) == "ยี่สิบห้าสตางค์"
    assert baht_text(0) == "ศูนย์บาทถ้วน"
    assert baht_text(1000000) == "หนึ่งล้านบาทถ้วน"


def test_attach_pidet_lines_groups_by_billno():
    bills = [{"BILLNO": "IV1", "AFTERTAX": 100.0}, {"BILLNO": "IV2", "AFTERTAX": 50.0}]
    lines = [
        {"BILLNO": "IV1", "QTY": 2, "PRICE": 40, "AMOUNT": 80, "DETAIL": "A"},
        {"BILLNO": "IV1", "QTY": 1, "PRICE": 20, "AMOUNT": 20, "DETAIL": "B"},
        {"BILLNO": "IV2", "QTY": 1, "PRICE": 50, "AMOUNT": 50, "DETAIL": "C"},
    ]
    out = attach_pidet_lines(bills, lines)
    assert [len(b["lines"]) for b in out] == [2, 1]
    assert out[0]["lines"][0]["DETAIL"] == "A"
    assert out[1]["lines"][0]["DETAIL"] == "C"


def test_note_totals_uses_reminder_discount_before_voucher():
    totals = _note_totals({"BILLAMT": 19025, "BILLCNT": 6}, {"discount_amount": 570.75})
    assert totals["billamt"] == 19025
    assert totals["discount"] == 570.75
    assert totals["netamt"] == 18454.25
    assert totals["net_text"] == "หนึ่งหมื่นแปดพันสี่ร้อยห้าสิบสี่บาทยี่สิบห้าสตางค์"


def test_note_totals_prefers_voucher_net():
    totals = _note_totals(
        {"BILLAMT": 100, "DISCOUNT": 10, "NETAMT": 90, "voucno": "KCPN6908-001", "BILLCNT": 1},
        {"discount_amount": 10},
    )
    assert totals["netamt"] == 90
    assert totals["net_text"] == "เก้าสิบบาทถ้วน"


def test_note_detail_api_includes_pidet_lines():
    from unittest.mock import MagicMock, patch

    from fastapi.testclient import TestClient
    from src.stock_check.auth import StockCheckIdentity

    ident = StockCheckIdentity(
        line_user_id="u1", display_name="Tester", branch="HQ", app="pay-notes"
    )
    header = {
        "acctno": "BRC",
        "acctname": "บ.ไอซีนคลัช",
        "noteno": "N-001",
        "voucno": "KCPN6908-046",
        "VOUCDATE": "2026-08-28",
        "BILLAMT": 19025,
        "DISCOUNT": 570.75,
        "NETAMT": 18454.25,
        "BILLCNT": 1,
    }
    bills = [
        {
            "BILLNO": "IV69080102",
            "BILLDATE": "2026-08-01",
            "AFTERTAX": 1900.0,
            "REMARKS": "",
            "lines": [
                {
                    "BILLNO": "IV69080102",
                    "BCODE": "CL-01",
                    "DETAIL": "คลัช",
                    "QTY": 2,
                    "UI": "ชิ้น",
                    "PRICE": 800.0,
                    "AMOUNT": 1600.0,
                    "LINE": 1,
                }
            ],
        }
    ]
    payments = [
        {
            "CHKNO": "โอน",
            "CHKDATE": "2026-08-28",
            "CHKAMT": 18454.25,
            "BANKNAME": "ไทยพาณิชย์ # 420-0-24341-0",
            "settle_method": "transfer",
        }
    ]

    with (
        patch("app.routers.pay_notes._require_api", return_value=(ident, None)),
        patch("app.routers.pay_notes.get_note_header", return_value=header),
        patch("app.routers.pay_notes.get_pay_notes_supabase_client", return_value=MagicMock()),
        patch("app.routers.pay_notes.list_folder", return_value=[]),
        patch("app.routers.pay_notes.list_vendor_banks", return_value=[]),
        patch("app.routers.pay_notes.get_reminder", return_value={"discount_amount": 570.75, "due_date": "2026-09-30"}),
        patch("app.routers.pay_notes.get_vendor_bank", return_value=None),
        patch("app.routers.pay_notes.list_note_bills_with_lines", return_value=bills),
        patch("app.routers.pay_notes.list_voucher_payments", return_value=payments),
        patch("app.routers.pay_notes.get_pay_notes_settings") as settings_m,
    ):
        settings_m.return_value.site = "HQ"
        from app.pay_notes_app import app

        client = TestClient(app)
        res = client.get("/pay-notes/api/notes/BRC/N-001")
    assert res.status_code == 200
    body = res.json()
    assert body["bills"][0]["lines"][0]["QTY"] == 2
    assert body["bills"][0]["lines"][0]["PRICE"] == 800.0
    assert body["payments"][0]["CHKNO"] == "โอน"
    assert body["totals"]["netamt"] == 18454.25
    assert body["totals"]["net_text"] == "หนึ่งหมื่นแปดพันสี่ร้อยห้าสิบสี่บาทยี่สิบห้าสตางค์"
