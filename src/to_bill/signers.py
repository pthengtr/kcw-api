"""Fixed seller signatories for full tax invoices / receipts."""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

from src.to_bill.errors import ToBillError

_SIG_DIR = Path(__file__).resolve().parent / "signatures"

# Issuer (ผู้ออกเอกสาร) and approver (ผู้อนุมัติเอกสาร) are fixed people.
ISSUER = {
    "nick": "อ้อน",
    "full_name": "มัญชุนันท์ คำลา",
    "role": "ผู้ออกเอกสาร",
    "image": "aon.jpg",
    "aliases": ("อ้อน", "มัญชุนันท์", "คำลา", "aon", "manchunan"),
}
APPROVER = {
    "nick": "เมย์",
    "full_name": "ปิยะนุช นันตาบุตร",
    "role": "ผู้อนุมัติเอกสาร",
    "image": "may.jpg",
    "aliases": ("เมย์", "เมย", "ปิยะนุช", "นันตาบุตร", "may", "piyanuch"),
}

_ALLOWED = (ISSUER, APPROVER)


def _tokens(value: str) -> set[str]:
    raw = value or ""
    compact = "".join(raw.split()).casefold()
    tokens = {compact} if compact else set()
    for word in re.split(r"[\s\-_/.,]+", raw):
        cleaned = "".join(ch for ch in word.casefold() if ch.isalnum())
        if cleaned:
            tokens.add(cleaned)
    return tokens


def match_signer(actor: str) -> dict | None:
    tokens = _tokens(actor)
    if not tokens:
        return None
    for signer in _ALLOWED:
        aliases = {"".join(a.split()).casefold() for a in signer["aliases"]}
        if tokens & aliases:
            return signer
    return None


def can_issue(actor: str) -> bool:
    return match_signer(actor) is not None


def assert_can_issue(actor: str) -> None:
    if can_issue(actor):
        return
    raise ToBillError(
        "not_allowed",
        "ออกเอกสารได้เฉพาะ อ้อน (มัญชุนันท์ คำลา) หรือ เมย์ (ปิยะนุช นันตาบุตร)",
        status=403,
    )


def display_name(signer: dict) -> str:
    return f"{signer['nick']} - {signer['full_name']} เป็น{signer['role']}"


@lru_cache
def signature_data_uri(filename: str) -> str:
    path = _SIG_DIR / filename
    raw = path.read_bytes()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    suffix = path.suffix.lower().lstrip(".") or "jpeg"
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
    return f"data:{mime};base64,{b64}"
