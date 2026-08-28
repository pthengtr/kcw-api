from src.handlers.pay_notes_entry import is_pay_notes_command
from src.pay_notes.net import rewrite_base_port
from src.pay_notes.ui import initials, page
from src.pay_notes.writer import PayNoteWriteError, create_pay_note
from src.pay_notes.config import PayNotesSettings
from src.pay_notes.parts9 import infer_settle_method


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
    assert "จ่ายแล้ว" in html
    assert "themeBtn" in html
    assert "kcw.pay_notes.theme" in html
    assert 'id="tabNotes"' in html
    assert 'id="tabPending"' in html
    assert 'id="tabVouchers"' in html
    assert 'id="tabCreate"' not in html
    assert 'id="tabAwaitProof"' not in html
    assert 'id="tabPaid"' not in html
    assert ">สร้างโน้ต<" not in html
    assert ">ค้างจ่าย<" not in html
    assert 'id="tabProof"' not in html
    assert "ทด" in html  # avatar initials


def test_page_has_voucher_and_proof_tabs():
    html = page(user_name="Alice Doe", site="HQ", write_enabled=True)
    assert "ใบสำคัญจ่าย" in html
    assert "บันทึกการจ่าย" in html
    assert "WRITE_ENABLED = true" in html
    assert "/vouchers" in html
    assert "/vouchered" in html
    assert "AD" in html


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
