from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.handlers.receive_notes_entry import is_receive_notes_command
from src.receive_notes.company_banks import brdet_line_from_payment, resolve_company_receive_account
from src.receive_notes.noteno import buddhist_yymm, note_stem
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


def test_voucher_stems_match_mined_series():
    when = datetime(2026, 11, 18, tzinfo=ZoneInfo("Asia/Bangkok"))
    assert buddhist_yymm(when) == "6911"
    assert voucher_stem("2", when) == "6911-"
    assert voucher_stem("1", when) == "RC6911-"
    assert note_stem(when) == "BN6911-"


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
    assert "KBANK" in line["bankname"]


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


def test_company_receive_default():
    acct = resolve_company_receive_account(None)
    assert acct["key"] == "kbank_91723"


def test_tiger_ar_source_key():
    rid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    key = ar_pos_bill_id(rid)
    assert key.startswith("ar:")
    assert is_ar_pos_bill_id(key)
    assert receipt_id_from_pos_bill_id(key) == rid
    assert not is_ar_pos_bill_id("pos-bill-1")
