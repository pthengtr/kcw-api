from __future__ import annotations

from typing import Any

# HQ company accounts that receive customer transfers (BRDET.ACCTNO = GL).
# Labels locked by ops; GLs from prior BRDET mining + AP payout map for shared accounts.
COMPANY_RECEIVE_ACCOUNTS: dict[str, dict[str, str]] = {
    "ktb_44244": {
        "key": "ktb_44244",
        "label": "กรุงไทย 248-0-44244-6",
        "bank_name": "กรุงไทย 248-0-44244-6",
        "account_no": "248-0-44244-6",
        "gl": "2101.7",
    },
    "ktb_00138": {
        "key": "ktb_00138",
        "label": "กรุงไทย 248-6-00138-7",
        "bank_name": "กรุงไทย 248-6-00138-7",
        "account_no": "248-6-00138-7",
        "gl": "2101.4",
    },
    "ktb_42113": {
        "key": "ktb_42113",
        "label": "กรุงไทย 248-0-42113-9",
        "bank_name": "กรุงไทย 248-0-42113-9",
        "account_no": "248-0-42113-9",
        "gl": "2101.3",
    },
    "kbank_91723": {
        "key": "kbank_91723",
        "label": "กสิกร 064-8-91723-6",
        "bank_name": "กสิกร 064-8-91723-6",
        "account_no": "064-8-91723-6",
        "gl": "2101.1",
    },
    "kbank_92039": {
        "key": "kbank_92039",
        "label": "กสิกร 064-8-92039-3",
        "bank_name": "กสิกร 064-8-92039-3",
        "account_no": "064-8-92039-3",
        "gl": "2101.6",
    },
}

DEFAULT_RECEIVE_BANK_KEY = "ktb_44244"

# Backward-compatible aliases for older keys in overlay / tests
_ALIASES = {
    "ktb_04211": "ktb_42113",
}


def list_company_receive_accounts() -> list[dict[str, str]]:
    return [dict(v) for v in COMPANY_RECEIVE_ACCOUNTS.values()]


def resolve_company_receive_account(key: str | None) -> dict[str, str]:
    raw = (key or DEFAULT_RECEIVE_BANK_KEY).strip()
    k = _ALIASES.get(raw, raw)
    acct = COMPANY_RECEIVE_ACCOUNTS.get(k)
    if acct:
        return dict(acct)
    return dict(COMPANY_RECEIVE_ACCOUNTS[DEFAULT_RECEIVE_BANK_KEY])


def resolve_optional_receive_account(key: str | None) -> dict[str, str] | None:
    """Resolve receive bank for billing-note print; empty key → None (optional)."""
    raw = (key or "").strip()
    if not raw:
        return None
    k = _ALIASES.get(raw, raw)
    acct = COMPANY_RECEIVE_ACCOUNTS.get(k)
    return dict(acct) if acct else None


def receive_bank_key_from_gl(gl: str | None) -> str | None:
    """Map BRDET.ACCTNO (GL) back to a company receive-bank key."""
    needle = (gl or "").strip()
    if not needle:
        return None
    for key, acct in COMPANY_RECEIVE_ACCOUNTS.items():
        if str(acct.get("gl") or "").strip() == needle:
            return key
    return None


def receive_bank_key_from_bankname(bankname: str | None) -> str | None:
    """Best-effort match BRDET.BANKNAME to a company receive-bank key."""
    needle = (bankname or "").strip()
    if not needle:
        return None
    for key, acct in COMPANY_RECEIVE_ACCOUNTS.items():
        if needle == str(acct.get("bank_name") or "").strip():
            return key
        if needle == str(acct.get("label") or "").strip():
            return key
        if needle in str(acct.get("bank_name") or ""):
            return key
    return None


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
