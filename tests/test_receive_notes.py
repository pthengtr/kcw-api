from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.handlers.receive_notes_entry import is_receive_notes_command
from src.receive_notes.company_banks import (
    brdet_line_from_payment,
    list_company_receive_accounts,
    resolve_company_receive_account,
)
from src.receive_notes.noteno import buddhist_yymm, note_stem
from src.receive_notes.parts9 import infer_settle_method
from src.receive_notes.tiger import ar_pos_bill_id, is_ar_pos_bill_id, receipt_id_from_pos_bill_id
from src.receive_notes.writer import voucher_stem
from src.staff_shell.catalog import get_service


def test_receive_notes_commands():
    assert is_receive_notes_command("รับชำระลูกหนี้")
    assert is_receive_notes_command("รับชำระ")
    assert is_receive_notes_command("receivenote")
    assert is_receive_notes_command(" receive note ")
    assert not is_receive_notes_command("ชำระเจ้าหนี้")


def test_catalog_entry():
    svc = get_service("receive-notes")
    assert svc is not None
    assert svc.port == 8797
    assert svc.path == "/receive-notes/"
    assert "HQ" in svc.hosts
    assert svc.icon == "ar"


def test_number_stems_match_product_series():
    when = datetime(2026, 11, 18, tzinfo=ZoneInfo("Asia/Bangkok"))
    assert buddhist_yymm(when) == "6911"
    # VAT
    assert note_stem("1", when) == "BN6911-"
    assert voucher_stem("1", when) == "RC6911-"
    # Non-VAT
    assert note_stem("2", when) == "BNN6911-"
    assert voucher_stem("2", when) == "RCN6911-"
    # Marketplace TAD → RVI
    assert voucher_stem("1", when, acctno="7LAZ1") == "RVI6911-"
    assert voucher_stem("2", when, acctno="7SP") == "RVI6911-"
    assert voucher_stem("1", when, acctno="7ICE") == "RVI6911-"


def test_proof_required_skips_cash_and_rvi():
    from src.receive_notes.writer import proof_required, uses_rvi_voucher

    assert uses_rvi_voucher("7LAZ1")
    assert uses_rvi_voucher("7iaps")
    assert not uses_rvi_voucher("C001")
    assert proof_required(voucno="RC6911-001", settle_method="transfer") is True
    assert proof_required(voucno="RC6911-001", settle_method="cash") is False
    assert proof_required(voucno="RVI6911-001", settle_method="transfer") is False
    assert proof_required(voucno="RVI6911-001", settle_method="cash") is False


def test_brdet_transfer_line():
    line = brdet_line_from_payment(
        settle_method="transfer",
        chkno="",
        chkamt=100.0,
        chkdate="2026-11-18",
        receive_bank_key="kbank_91723",
    )
    assert line["chkno"] == "โอน"
    assert line["acctno"] == "2101.1"
    assert "91723" in line["bankname"]


def test_brdet_cash_line():
    line = brdet_line_from_payment(
        settle_method="cash",
        chkno="",
        chkamt=50,
        chkdate="2026-11-18",
        tiger_payment_no="PA2601",
    )
    assert line["chkno"] == "PA2601"
    assert line["bankname"] == ""
    assert line["acctno"] == ""


def test_company_receive_accounts_product_list():
    labels = {a["label"] for a in list_company_receive_accounts()}
    assert labels == {
        "กรุงไทย 248-0-44244-6",
        "กรุงไทย 248-6-00138-7",
        "กรุงไทย 248-0-42113-9",
        "กสิกร 064-8-91723-6",
        "กสิกร 064-8-92039-3",
    }
    acct = resolve_company_receive_account(None)
    assert acct["key"] == "ktb_44244"
    # legacy alias
    assert resolve_company_receive_account("ktb_04211")["key"] == "ktb_42113"


def test_tiger_ar_source_key():
    rid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    key = ar_pos_bill_id(rid)
    assert key.startswith("ar:")
    assert is_ar_pos_bill_id(key)
    assert receipt_id_from_pos_bill_id(key) == rid
    assert not is_ar_pos_bill_id("pos-bill-1")


def test_tiger_cash_skips_non_ar_pos_bill():
    from src.receive_notes.service import complete_tiger_receipt_for_pos_bill

    assert complete_tiger_receipt_for_pos_bill(pos_bill_id="sale-123") is None
    assert complete_tiger_receipt_for_pos_bill(pos_bill_id="") is None


def test_duplicate_note_key_error_detection():
    from src.receive_notes.db import is_duplicate_note_key_error

    assert is_duplicate_note_key_error(
        Exception('duplicate key value violates unique constraint "note_pkey"')
    )
    assert is_duplicate_note_key_error(Exception("code=23505"))
    err = Exception("boom")
    err.code = "23505"  # type: ignore[attr-defined]
    assert is_duplicate_note_key_error(err)
    assert not is_duplicate_note_key_error(Exception("connection reset"))


def test_ensure_open_note_reactivates_canceled(monkeypatch):
    from src.receive_notes import db as rn_db

    calls: dict[str, object] = {}

    def fake_get(_client, acctno, noteno):
        calls["get"] = (acctno, noteno)
        return {"acctno": acctno, "noteno": noteno, "status": "canceled"}

    def fake_patch(_client, acctno, noteno, patch):
        calls["patch"] = (acctno, noteno, patch)
        return {"acctno": acctno, "noteno": noteno, **patch}

    def fail_insert(*_a, **_k):
        raise AssertionError("insert should not run when overlay exists")

    monkeypatch.setattr(rn_db, "get_note", fake_get)
    monkeypatch.setattr(rn_db, "patch_note", fake_patch)
    monkeypatch.setattr(rn_db, "insert_note", fail_insert)

    out = rn_db.ensure_open_note(
        object(),
        {
            "acctno": "TEST",
            "noteno": "BNN6911-007",
            "jourmode": "2",
            "status": "open",
            "due_date": "2026-11-22",
            "discount_mode": "amount",
            "discount_input": 0,
            "discount_amount": 0,
        },
    )
    assert out["status"] == "open"
    assert calls["get"] == ("TEST", "BNN6911-007")
    assert calls["patch"][0] == "TEST"
    assert calls["patch"][2]["status"] == "open"


def test_ensure_open_note_blocks_received(monkeypatch):
    from src.receive_notes import db as rn_db

    monkeypatch.setattr(
        rn_db,
        "get_note",
        lambda *_a, **_k: {"acctno": "TEST", "noteno": "BNN6911-001", "status": "received"},
    )
    try:
        rn_db.ensure_open_note(
            object(),
            {"acctno": "TEST", "noteno": "BNN6911-001", "jourmode": "2", "status": "open"},
        )
        assert False, "expected NoteOverlayConflict"
    except rn_db.NoteOverlayConflict as exc:
        assert exc.code == "already_received"


def test_ui_exports_and_tabs():
    from src.receive_notes import ui as rn_ui

    assert rn_ui.APP == "receive-notes"
    assert rn_ui.SESSION_COOKIE == "kcw_receive_notes"
    html = rn_ui.page(user_name="Test", site="HQ", write_enabled=False)
    assert "รับชำระลูกหนี้" in html
    assert "รอรับชำระ" in html
    assert "ใบเสร็จรับเงิน" in html
    assert "ใบสำคัญรับเงิน" not in html
    assert "บัญชีสำหรับรับชำระ" in html
    assert "ค้นหาตามลูกหนี้" in html
    assert "กรอกเอง" not in html
    assert "ช่วยอ่านเอกสาร" not in html
    assert "เตือนโอน KBIZ" not in html
    assert "จำนวนเงินที่รับ" in html
    assert "บัญชีที่รับเงิน" in html
    assert "รับชำระ" in html
    assert "บันทึกและรับชำระ" in html
    assert "btnCreateAndPay" in html
    assert "createNote({ openPayAfter: true })" in html
    assert "createInFlight" in html
    assert "detEditMetaBtn" in html
    assert "dlgEditReceipt" in html
    # Mobile proof upload: opaque overlay input (not display:none + JS click)
    assert 'id="dropProofWrap"' in html
    assert 'class="drop-file-input"' in html
    assert 'id="detProofFiles" class="hidden"' not in html
    assert "แตะหรือคลิกเพื่อเลือกไฟล์" in html
    # Negative BN/BNN → refund labels (same dialog / tabs, no new tab)
    assert "บันทึกและคืนเงินลูกค้า" in html
    assert "syncCreatePayButton" in html
    assert "รอคืนเงิน" in html
    assert "ยอดค้างคืน" in html
    assert "คืนเงินลูกค้า" in html
    assert "ใบสำคัญจ่าย" in html
    # Cash refund shows Tiger voucher QR (KCN pattern) in the same pay dialog
    assert "renderTigerAwaiting" in html
    assert "tiger-voucher-box" in html
    assert "สแกน QR ที่ตู้ Tiger เพื่อจ่ายเงินสด" in html
    assert "รอเครื่องยืนยันจ่ายคืนเงินสด" in html
    assert "Tiger voucher QR" in html
    # Tiger cash poll on existing pay dialog (no new page)
    assert "pollTigerVoucher" in html
    assert "/vouchers/tiger-status" in html
    assert "รอ Tiger ยืนยันรับเงินสด" in html
    # AR brand accent (Deep Teal)
    assert "#247B74" in html
    assert "formatDiscountLabel" in html
    # pending board no longer filters/columns by settle method
    assert "pfMethod" not in html
    # canceled notes must not stay on รอรับชำระ (history via ค้นหาตามลูกหนี้)
    assert "keep canceled visible in \"all\"" not in html
    assert "if (isCanceledRow(r)) return false;" in html


def test_pvn_refund_voucher_stem():
    when = datetime(2026, 11, 23, tzinfo=ZoneInfo("Asia/Bangkok"))
    from src.receive_notes.writer import voucher_stem

    assert voucher_stem("1", when, refund=True) == "PVN6911-"
    assert voucher_stem("2", when, refund=True) == "PVN6911-"
    assert voucher_stem("1", when, refund=False) == "RC6911-"
    assert voucher_stem("2", when, refund=False) == "RCN6911-"


def test_tiger_ar_refund_source_key():
    from src.receive_notes.tiger import (
        ar_refund_pos_bill_id,
        is_ar_refund_pos_bill_id,
        receipt_id_from_pos_bill_id,
    )

    rid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    key = ar_refund_pos_bill_id(rid)
    assert key.startswith("ar-refund:")
    assert is_ar_refund_pos_bill_id(key)
    assert not is_ar_pos_bill_id(key)
    assert receipt_id_from_pos_bill_id(key) == rid


def test_ar_refund_voucher_display_builds_qr():
    """Cash refund API must expose scannable QR like KCN companion voucher."""
    from src.receive_notes.tiger import ar_refund_voucher_display

    display = ar_refund_voucher_display(
        {
            "voucher_num": "082475711990",
            "status": "pending",
            "raw_status": "pending",
            "raw_create_response": {"data": {"voucher_num": "082475711990", "used": "N"}},
        }
    )
    assert display is not None
    assert display["voucher_num"] == "082475711990"
    assert display["code"] == "082475711990"
    assert str(display.get("qr_image") or "").startswith("data:image/png;base64,")


def test_note_refund_snapshot(monkeypatch):
    from src.receive_notes import service as rn_svc

    monkeypatch.setattr(rn_svc, "confirmed_refund_total", lambda *_a, **_k: 400.0)
    snap = rn_svc.note_refund_snapshot(
        acctno="C001", noteno="BNN6911-001", note_net=-1500.0, client=object()
    )
    assert snap["is_refund"] is True
    assert snap["credit_amt"] == 1500.0
    assert snap["refunded_amt"] == 400.0
    assert snap["remaining_refund"] == 1100.0

    snap2 = rn_svc.note_refund_snapshot(
        acctno="C001", noteno="BN6911-002", note_net=500.0, client=object()
    )
    assert snap2["is_refund"] is False
    assert snap2["remaining_refund"] == 0.0


def test_pay_notes_ui_ap_accent_and_discount_label():
    from src.pay_notes import ui as pn_ui

    html = pn_ui.page(user_name="Test", site="HQ", write_enabled=False)
    # AP brand accent (Deep Blue)
    assert "#315C83" in html
    assert "formatDiscountLabel" in html


def test_infer_settle_method_prefers_bank_gl():
    assert infer_settle_method("", bankname="", acctno="") == "cash"
    assert infer_settle_method("โอน", bankname="กสิกร", acctno="2101.1") == "transfer"
    assert infer_settle_method("PA2601", bankname="", acctno="") == "cash"
    assert infer_settle_method("123456", bankname="กรุงไทย", acctno="") == "cheque"


def test_list_vouchered_notes_sets_settle_method_from_brdet(monkeypatch):
    """Tab 4 column วิธีรับชำระ reads top-level settle_method from /vouchered."""
    from datetime import date

    from src.receive_notes import parts9 as rn_parts9

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self

        def all(self):
            return self._rows

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def execute(self, sql, params=None):
            text_sql = str(sql)
            if "FROM dbo.RVMAS" in text_sql:
                return _Result(
                    [
                        {
                            "acctno": "C001",
                            "acctname": "ลูกค้า",
                            "noteno": "BNN6911-001",
                            "voucno": "RCN6911-001",
                            "VOUCDATE": date(2026, 11, 18),
                            "BILLAMT": 100.0,
                            "NETAMT": 100.0,
                            "PAYAMT": 100.0,
                            "CHKAMT": 100.0,
                            "DISCOUNT": 0.0,
                            "JOURMODE": "2",
                        },
                        {
                            "acctno": "7LAZ1",
                            "acctname": "Lazada",
                            "noteno": "BN6911-002",
                            "voucno": "RVI6911-001",
                            "VOUCDATE": date(2026, 11, 18),
                            "BILLAMT": 50.0,
                            "NETAMT": 50.0,
                            "PAYAMT": 50.0,
                            "CHKAMT": 50.0,
                            "DISCOUNT": 0.0,
                            "JOURMODE": "1",
                        },
                    ]
                )
            if "FROM dbo.BRDET" in text_sql:
                return _Result(
                    [
                        {
                            "voucno": "RCN6911-001",
                            "chkno": "โอน",
                            "bankname": "กสิกร",
                            "acctno": "2101.1",
                        },
                        {
                            "voucno": "RVI6911-001",
                            "chkno": "PA2601",
                            "bankname": "",
                            "acctno": "",
                        },
                    ]
                )
            raise AssertionError(f"unexpected sql: {text_sql}")

    class _Eng:
        def connect(self):
            return _Conn()

    monkeypatch.setattr(rn_parts9, "get_site_engine", lambda *_a, **_k: _Eng())

    overlays = [
        {"acctno": "C001", "noteno": "BNN6911-001", "settle_method": "transfer", "status": "received"},
        {"acctno": "7LAZ1", "noteno": "BN6911-002", "settle_method": "cash", "status": "received"},
    ]
    rows = rn_parts9.list_vouchered_notes("HQ", overlays)
    by_vo = {r["voucno"]: r for r in rows}
    assert by_vo["RCN6911-001"]["settle_method"] == "transfer"
    assert by_vo["RVI6911-001"]["settle_method"] == "cash"


def test_list_vouchered_notes_falls_back_to_overlay_when_brdet_missing(monkeypatch):
    from datetime import date

    from src.receive_notes import parts9 as rn_parts9

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self

        def all(self):
            return self._rows

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def execute(self, sql, params=None):
            text_sql = str(sql)
            if "FROM dbo.RVMAS" in text_sql:
                return _Result(
                    [
                        {
                            "acctno": "C001",
                            "acctname": "ลูกค้า",
                            "noteno": "BNN6911-001",
                            "voucno": "RCN6911-002",
                            "VOUCDATE": date(2026, 11, 18),
                            "BILLAMT": 100.0,
                            "NETAMT": 100.0,
                            "PAYAMT": None,
                            "CHKAMT": None,
                            "DISCOUNT": 0.0,
                            "JOURMODE": "2",
                        }
                    ]
                )
            if "FROM dbo.BRDET" in text_sql:
                return _Result([])
            raise AssertionError(f"unexpected sql: {text_sql}")

    class _Eng:
        def connect(self):
            return _Conn()

    monkeypatch.setattr(rn_parts9, "get_site_engine", lambda *_a, **_k: _Eng())
    rows = rn_parts9.list_vouchered_notes(
        "HQ",
        [{"acctno": "C001", "noteno": "BNN6911-001", "settle_method": "cheque", "status": "received"}],
    )
    assert len(rows) == 1
    assert rows[0]["settle_method"] == "cheque"


def test_optional_receive_account():
    from src.receive_notes.company_banks import resolve_optional_receive_account

    assert resolve_optional_receive_account("") is None
    assert resolve_optional_receive_account(None) is None
    assert resolve_optional_receive_account("kbank_91723")["key"] == "kbank_91723"


def test_resolve_discount_allows_negative_billamt():
    """ใบลดหนี้ nets are valid BN/BNN totals — not 'discount exceeds bill'."""
    from app.routers.receive_notes import _resolve_discount

    mode, raw, amount = _resolve_discount(-1500.0, "amount", 0.0)
    assert mode == "amount"
    assert raw == 0.0
    assert amount == 0.0

    mode, raw, amount = _resolve_discount(-500.0, "amount", -0.01)
    assert amount == -0.01

    # Positive bill still rejects discount above total.
    try:
        _resolve_discount(100.0, "amount", 100.01)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "discount exceeds" in str(exc)


def test_ui_disc_exceeds_allows_negative_bill_total():
    from src.receive_notes import ui as rn_ui

    html = rn_ui.page(user_name="Test", site="HQ", write_enabled=True)
    assert "function discExceedsBill" in html
    assert "Number(bill) >= 0 && Number(disc) - Number(bill) > 1e-9" in html
    assert "discExceedsBill(resolveDiscAmount(total), total)" in html
    assert "discExceedsBill(resolveEditDiscAmount(total), total)" in html


def test_assess_receive_edit_gate_flags_posted_and_bank_done():
    from src.receive_notes.parts9 import assess_receive_edit_gate

    open_gate = assess_receive_edit_gate(
        header={"POSTED1": "N", "POSTED2": "N", "DONE": "N"},
        payments=[{"DONE": "N"}],
    )
    assert open_gate["needs_accounting_review"] is False
    assert open_gate["reasons"] == []

    posted = assess_receive_edit_gate(
        header={"POSTED1": "Y", "POSTED2": "N", "DONE": "N"},
        payments=[{"DONE": "N"}],
    )
    assert posted["needs_accounting_review"] is True
    assert "period_closed" in posted["reasons"]

    bank = assess_receive_edit_gate(
        header={"POSTED1": "N", "POSTED2": "N", "DONE": "N"},
        payments=[{"DONE": "Y"}],
    )
    assert bank["needs_accounting_review"] is True
    assert "bank_reconciled" in bank["reasons"]


def test_receive_bank_key_from_gl_and_name():
    from src.receive_notes.company_banks import (
        receive_bank_key_from_bankname,
        receive_bank_key_from_gl,
    )

    assert receive_bank_key_from_gl("2101.7") == "ktb_44244"
    assert receive_bank_key_from_gl("") is None
    assert receive_bank_key_from_bankname("กสิกร 064-8-91723-6") == "kbank_91723"


def test_ui_has_voucher_meta_edit_controls():
    from src.receive_notes import ui as rn_ui

    html = rn_ui.page(user_name="Test", site="HQ", write_enabled=True)
    assert 'id="detEditMetaBtn"' in html
    assert "แก้ไขข้อมูลรับชำระ" in html
    assert "/api/vouchers/meta" in html
    assert "accounting_reviewed" in html
    assert "editRcptAcctAck" in html
    assert "ประวัติการแก้ไข" in html


def test_voucher_meta_edit_model_fields():
    from app.routers.receive_notes import VoucherMetaEdit

    body = VoucherMetaEdit(
        acctno="C001",
        noteno="BN6911-001",
        received_at="2026-11-20",
        remark="แก้วันที่",
        receive_bank_key="ktb_44244",
        accounting_reviewed=True,
    )
    assert body.acctno == "C001"
    assert body.accounting_reviewed is True


def test_get_receipt_by_voucno_uses_limit_not_maybe_single():
    import inspect

    from src.receive_notes import db as rn_db

    src = inspect.getsource(rn_db.get_receipt_by_voucno)
    assert ".maybe_single(" not in src
    assert ".limit(1)" in src


def test_list_receipt_edit_audits_soft_fails(monkeypatch):
    from src.receive_notes import db as rn_db

    class Boom:
        def schema(self, *_a, **_k):
            raise RuntimeError("PGRST205 schema cache")

    assert rn_db.list_receipt_edit_audits(Boom(), voucno="RV6911-001") == []
