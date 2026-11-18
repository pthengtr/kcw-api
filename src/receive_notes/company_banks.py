from __future__ import annotations

from typing import Any

# HQ company accounts that receive customer transfers (BRDET.ACCTNO = GL).
# Names/GLs mined from recent CR BRDET rows (2026-11).
COMPANY_RECEIVE_ACCOUNTS: dict[str, dict[str, str]] = {
    "kbank_91723": {
        "key": "kbank_91723",
        "label": "กสิกร 064-8-91723-6",
        "bank_name": "KBANK 064-8-91723-6",
        "account_no": "064-8-91723-6",
        "gl": "2101.1",
    },
    "ktb_04211": {
        "key": "ktb_04211",
        "label": "กรุงไทย 248-0-42113-9",
        "bank_name": "KBTK 2480421139",
        "account_no": "248-0-42113-9",
        "gl": "2101.3",
    },
    "ktb_00138": {
        "key": "ktb_00138",
        "label": "กรุงไทย 248-6-00138-7",
        "bank_name": "กรุงไทย 2486001387",
        "account_no": "248-6-00138-7",
        "gl": "2101.4",
    },
}

DEFAULT_RECEIVE_BANK_KEY = "kbank_91723"


def list_company_receive_accounts() -> list[dict[str, str]]:
    return [dict(v) for v in COMPANY_RECEIVE_ACCOUNTS.values()]


def resolve_company_receive_account(key: str | None) -> dict[str, str]:
    k = (key or DEFAULT_RECEIVE_BANK_KEY).strip()
    acct = COMPANY_RECEIVE_ACCOUNTS.get(k)
    if acct:
        return dict(acct)
    return dict(COMPANY_RECEIVE_ACCOUNTS[DEFAULT_RECEIVE_BANK_KEY])


def brdet_line_from_payment(
    *,
    settle_method: str,
    chkno: str,
    chkamt: float,
    chkdate: str,
    receive_bank_key: str | None = None,
    tiger_payment_no: str | None = None,
) -> dict[str, Any]:
    """Build one BRDET row for an AR receipt voucher."""
    method = (settle_method or "transfer").strip().lower()
    ref = (chkno or "").strip()
    if method == "transfer":
        if not ref:
            ref = "โอน"
        bank = resolve_company_receive_account(receive_bank_key)
        return {
            "settle_method": "transfer",
            "chkno": ref[:15],
            "chkamt": round(float(chkamt or 0), 2),
            "bankname": bank["bank_name"][:60],
            "acctno": bank["gl"][:10],
            "paytype": 2,
            "chkdate": chkdate,
            "receive_bank_key": bank["key"],
        }
    if method in ("cheque", "check"):
        if not ref:
            raise ValueError("cheque number required")
        return {
            "settle_method": "cheque",
            "chkno": ref[:15],
            "chkamt": round(float(chkamt or 0), 2),
            "bankname": (receive_bank_key or "").strip()[:60] or None,
            "acctno": None,
            "paytype": 2,
            "chkdate": chkdate,
            "receive_bank_key": None,
        }
    # cash (tiger or manual)
    tiger_ref = (tiger_payment_no or ref or "").strip()
    return {
        "settle_method": "cash",
        "chkno": (tiger_ref[:15] if tiger_ref else None),
        "chkamt": round(float(chkamt or 0), 2),
        "bankname": "",
        "acctno": "",
        "paytype": 2,
        "chkdate": chkdate,
        "receive_bank_key": None,
    }
