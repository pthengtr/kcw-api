from __future__ import annotations

import re
from dataclasses import dataclass

_GENERIC = ("lazada", "shopee", "tiktok", "เงินสด", "คุณลูกค้าทั่วไป")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Buyer:
    customer_name: str
    address: str
    phone: str
    tax_id: str
    branch_label: str
    email: str


def is_generic_party(name: str | None) -> bool:
    folded = (name or "").strip().lower()
    if not folded:
        return True
    return any(token in folded for token in _GENERIC)


def usable_tax_id(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 13:
        return ""
    if not digits.strip("0") or digits.startswith("000000000000"):
        return ""
    return digits


def normalize_branch(label: str | None, branch_no: str | None = None) -> str:
    raw = (label or "").strip()
    number = re.sub(r"\D", "", branch_no or "")
    if raw.startswith("สาขา") or number:
        if not number:
            number = re.sub(r"\D", "", raw)
        if not number:
            raise ValueError("branch")
        n = int(number)
        if n < 1 or n > 99999:
            raise ValueError("branch")
        return f"สาขาที่ {n}"
    return "สำนักงานใหญ่"


def parse_buyer(payload: dict | None) -> Buyer:
    data = payload or {}
    try:
        branch = normalize_branch(
            str(data.get("branch_label") or data.get("branch") or ""),
            str(data.get("branch_no") or ""),
        )
    except ValueError as exc:
        raise ValueError("ระบุเลขสาขา") from exc
    return Buyer(
        customer_name=str(data.get("customer_name") or "").strip(),
        address=str(data.get("address") or "").strip(),
        phone=str(data.get("phone") or "").strip(),
        tax_id=re.sub(r"\D", "", str(data.get("tax_id") or "")),
        branch_label=branch,
        email=str(data.get("email") or "").strip(),
    )


def validate_buyer(buyer: Buyer) -> str | None:
    if not buyer.customer_name:
        return "กรอกชื่อผู้ซื้อ"
    if len(buyer.customer_name) > 200:
        return "ชื่อผู้ซื้อยาวเกินไป"
    if not buyer.address:
        return "กรอกที่อยู่ผู้ซื้อ"
    if len(buyer.address) > 500:
        return "ที่อยู่ยาวเกินไป"
    if len(buyer.tax_id) != 13:
        return "เลขประจำตัวผู้เสียภาษีต้องมี 13 หลัก"
    if not usable_tax_id(buyer.tax_id):
        return "เลขประจำตัวผู้เสียภาษีไม่ใช่เลขจริง"
    if len(buyer.phone) > 40:
        return "เบอร์โทรยาวเกินไป"
    if buyer.email:
        if len(buyer.email) > 120 or not _EMAIL.match(buyer.email):
            return "อีเมลไม่ถูกต้อง"
    return None


def armas_prefill(row: dict | None) -> dict | None:
    """Buyer suggestion from ARMAS. Marketplace accounts are not a buyer."""
    if not row:
        return None
    name = str(row.get("acctname") or "").strip()
    if is_generic_party(name):
        return None
    tax_id = usable_tax_id(str(row.get("tax_id") or ""))
    address = _join_address(row.get("addr1"), row.get("addr2"))
    phone = str(row.get("phone") or "").strip()
    email = str(row.get("email") or "").strip()
    if not name and not address and not tax_id:
        return None
    return {
        "customer_name": name,
        "address": address,
        "phone": phone,
        "tax_id": tax_id,
        "email": email,
        "branch_label": "สำนักงานใหญ่",
    }


def _join_address(addr1, addr2) -> str:
    parts: list[str] = []
    for raw in (addr1, addr2):
        text = str(raw or "").strip()
        if not text or text.upper() == "=DONE=":
            continue
        parts.append(text)
    return " ".join(parts)
