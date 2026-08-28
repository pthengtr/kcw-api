from __future__ import annotations

from typing import Any

# HQ company accounts used to pay vendors (BPDET = instrument from these accounts).
COMPANY_PAY_ACCOUNTS: dict[str, dict[str, str]] = {
    "ktb_44244": {
        "key": "ktb_44244",
        "label": "กรุงไทย 248-0-44244-6",
        "bank_name": "กรุงไทย 248-0-44244-6",
        "account_no": "248-0-44244-6",
        "gl": "2101.7",
    },
    "kbank_72355": {
        "key": "kbank_72355",
        "label": "กสิกร 141-1-72355-7",
        "bank_name": "กสิกร 141-1-72355-7",
        "account_no": "141-1-72355-7",
        "gl": "2101.1",
    },
}

DEFAULT_PAY_BANK_KEY = "ktb_44244"


def list_company_pay_accounts() -> list[dict[str, str]]:
    return [dict(v) for v in COMPANY_PAY_ACCOUNTS.values()]


def resolve_company_pay_account(key: str | None) -> dict[str, str]:
    k = (key or DEFAULT_PAY_BANK_KEY).strip()
    acct = COMPANY_PAY_ACCOUNTS.get(k)
    if acct:
        return dict(acct)
    return dict(COMPANY_PAY_ACCOUNTS[DEFAULT_PAY_BANK_KEY])


def bpdet_line_from_payment(
    *,
    settle_method: str,
    chkno: str,
    chkamt: float,
    chkdate: str,
    pay_bank_key: str,
) -> dict[str, Any]:
    """Build one BPDET row: ACCTNO = bank GL, BANKNAME = company payout account."""
    method = (settle_method or "transfer").strip().lower()
    ref = (chkno or "").strip()
    if method == "transfer" and not ref:
        ref = "โอน"
    if method == "cash":
        return {
            "chkno": ref[:15] if ref else None,
            "chkamt": round(float(chkamt or 0), 2),
            "bankname": "",
            "acctno": "",
            "paytype": 2,
            "chkdate": chkdate,
        }
    bank = resolve_company_pay_account(pay_bank_key)
    return {
        "chkno": ref,
        "chkamt": round(float(chkamt or 0), 2),
        "bankname": bank["bank_name"][:60],
        "acctno": bank["gl"][:10],
        "paytype": 2,
        "chkdate": chkdate,
    }
