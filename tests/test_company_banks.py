from src.pay_notes.company_banks import bpdet_line_from_payment, resolve_company_pay_account


def test_bpdet_uses_company_bank_not_vendor():
    line = bpdet_line_from_payment(
        settle_method="transfer",
        chkno="โอน",
        chkamt=1234.56,
        chkdate="2026-08-28",
        pay_bank_key="kbank_72355",
    )
    assert line["acctno"] == "2101.1"
    assert "72355" in line["bankname"]
    assert "141-1" in line["bankname"]
    assert line["chkno"] == "โอน"
    assert line["chkamt"] == 1234.56


def test_default_pay_bank_is_ktb():
    bank = resolve_company_pay_account(None)
    assert bank["account_no"] == "248-0-44244-6"
    assert bank["gl"] == "2101.7"
