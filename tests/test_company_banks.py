from src.pay_notes.company_banks import (
    DEFAULT_PAY_BANK_KEY,
    VENDOR_PREFIX_7_PAY_BANK_KEY,
    bpdet_line_from_payment,
    default_pay_bank_key_for_acctno,
    list_company_pay_accounts,
    resolve_company_pay_account,
)


def test_bpdet_uses_company_bank_not_vendor():
    line = bpdet_line_from_payment(
        settle_method="transfer",
        chkno="โอน",
        chkamt=1234.56,
        chkdate="2026-08-28",
        pay_bank_key="kbank_72355",
    )
    assert line["acctno"] == "2101.5"
    assert "72355" in line["bankname"]
    assert "141-1" in line["bankname"]
    assert line["chkno"] == "โอน"
    assert line["chkamt"] == 1234.56


def test_default_pay_bank_is_ktb():
    bank = resolve_company_pay_account(None)
    assert bank["account_no"] == "248-0-44244-6"
    assert bank["gl"] == "2101.7"


def test_default_pay_bank_by_vendor_acctno():
    assert default_pay_bank_key_for_acctno("71234") == VENDOR_PREFIX_7_PAY_BANK_KEY
    assert default_pay_bank_key_for_acctno("7ABC") == "kbank_72355"
    assert "3557" in resolve_company_pay_account(
        default_pay_bank_key_for_acctno("7001")
    )["account_no"].replace("-", "")
    assert default_pay_bank_key_for_acctno("61234") == DEFAULT_PAY_BANK_KEY
    assert default_pay_bank_key_for_acctno("BRC") == "ktb_44244"
    assert default_pay_bank_key_for_acctno("") == DEFAULT_PAY_BANK_KEY
    assert default_pay_bank_key_for_acctno(None) == DEFAULT_PAY_BANK_KEY
    assert "2446" in resolve_company_pay_account(
        default_pay_bank_key_for_acctno("A001")
    )["account_no"].replace("-", "")


def test_ktb_cheque_accounts_are_listed():
    by_key = {a["key"]: a for a in list_company_pay_accounts()}
    assert by_key["ktb_00618"]["account_no"] == "248-6-00618-4"
    assert by_key["ktb_00618"]["gl"] == "2101.2"
    assert by_key["ktb_00138"]["account_no"] == "248-6-00138-7"
    assert by_key["ktb_00138"]["gl"] == "2101.1"


def test_bpdet_cheque_uses_ktb_00618_gl():
    line = bpdet_line_from_payment(
        settle_method="cheque",
        chkno="10102938",
        chkamt=500.0,
        chkdate="2026-09-12",
        pay_bank_key="ktb_00618",
    )
    assert line["acctno"] == "2101.2"
    assert line["bankname"] == "กรุงไทย 248-6-00618-4"
    assert line["chkno"] == "10102938"


def test_bpdet_cheque_uses_ktb_00138_gl():
    line = bpdet_line_from_payment(
        settle_method="cheque",
        chkno="10102939",
        chkamt=750.0,
        chkdate="2026-09-12",
        pay_bank_key="ktb_00138",
    )
    assert line["acctno"] == "2101.1"
    assert line["bankname"] == "กรุงไทย 248-6-00138-7"
