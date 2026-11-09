"""Seller signatories for full tax invoices / receipts."""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

from src.to_bill.errors import ToBillError

_SIG_DIR = Path(__file__).resolve().parent / "signatures"

ROLE_ISSUER = "ผู้ออกเอกสาร"
ROLE_APPROVER = "ผู้อนุมัติเอกสาร"

AON = {
    "nick": "อ้อน",
    "full_name": "มัญชุนันท์ คำลา",
    "roles": (ROLE_ISSUER,),
    "image": "aon.jpg",
    # Real LINE display names include Manchunannnnn / Aon.
    "aliases": (
        "อ้อน",
        "มัญชุนันท์",
        "คำลา",
        "aon",
        "manchunan",
        "manchunannnnn",
    ),
}
MAY = {
    "nick": "เมย์",
    "full_name": "ปิยะนุช นันตาบุตร",
    "roles": (ROLE_APPROVER,),
    "image": "may.jpg",
    "aliases": ("เมย์", "เมย", "ปิยะนุช", "นันตาบุตร", "may", "piyanuch"),
}
CARTOON = {
    "nick": "การ์ตูน",
    "full_name": "จิดาภา กระจาย",
    "roles": (ROLE_ISSUER, ROLE_APPROVER),
    "image": "cartoon.jpg",
    # Real LINE display name is like Cartoonnnn!🦭 KCW.
    "aliases": (
        "การ์ตูน",
        "การตูน",
        "จิดาภา",
        "กระจาย",
        "cartoon",
        "cartoonnnn",
        "jidapa",
    ),
}

# Kept for older imports / tests that still say ISSUER / APPROVER.
ISSUER = AON
APPROVER = MAY

_ALLOWED = (AON, MAY, CARTOON)
_ALLOWED_LABEL = "อ้อน (มัญชุนันท์ คำลา) เมย์ (ปิยะนุช นันตาบุตร) หรือ การ์ตูน (จิดาภา กระจาย)"


def _tokens(value: str) -> set[str]:
    raw = value or ""
    compact = "".join(raw.split()).casefold()
    tokens = {compact} if compact else set()
    for word in re.split(r"[\s\-_/.,]+", raw):
        cleaned = "".join(ch for ch in word.casefold() if ch.isalnum())
        if cleaned:
            tokens.add(cleaned)
    return tokens


def _ascii_fuzzy(token: str, alias: str) -> bool:
    """LINE nicks often stretch letters (Manchunannnnn / Cartoonnnn)."""
    if not token.isascii() or not alias.isascii():
        return False
    if len(alias) < 4 or len(token) < 4:
        return False
    return token.startswith(alias) or alias.startswith(token)


def match_signer(actor: str) -> dict | None:
    tokens = _tokens(actor)
    if not tokens:
        return None
    for signer in _ALLOWED:
        aliases = {"".join(a.split()).casefold() for a in signer["aliases"]}
        if tokens & aliases:
            return signer
        for token in tokens:
            if any(_ascii_fuzzy(token, alias) for alias in aliases):
                return signer
    return None


def can_issue(actor: str) -> bool:
    return match_signer(actor) is not None


def assert_can_issue(actor: str) -> None:
    if can_issue(actor):
        return
    raise ToBillError(
        "not_allowed",
        f"ออกเอกสารได้เฉพาะ {_ALLOWED_LABEL}",
        status=403,
    )


def display_name(signer: dict) -> str:
    """Printed name on the sheet — full name only, no nickname."""
    return str(signer.get("full_name") or "").strip()


def sheet_signers(issued_by: str = "") -> tuple[dict, dict]:
    """Who fills the issuer / approver blocks.

    Default company pair is อ้อน + เมย์. การ์ตูน may sign both roles when she issues.
    """
    actor = match_signer(issued_by)
    if actor is CARTOON:
        return CARTOON, CARTOON
    return AON, MAY


@lru_cache
def signature_data_uri(filename: str) -> str:
    path = _SIG_DIR / filename
    raw = path.read_bytes()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    suffix = path.suffix.lower().lstrip(".") or "jpeg"
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
    return f"data:{mime};base64,{b64}"
