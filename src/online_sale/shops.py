from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from src.online_sale.errors import OnlineSaleError
from src.parts9_explorer.db import format_sql_error, get_site_engine

PLATFORMS = (
    ("shopee", "Shopee"),
    ("lazada", "Lazada"),
    ("tiktok", "TikTok"),
    ("line", "Line Shopping"),
)

_PLATFORM_KEYS = {k for k, _ in PLATFORMS}

# POS REMARKS stamp by marketplace (live TAD pattern). Line Shopping has no history yet.
PLATFORM_REMARKS = {
    "lazada": "##0000000000001",
    "tiktok": "##0000000000002",
    "shopee": "##0000000000003",
    "line": "##0000000000004",
}

# Non-marketplace 7* accounts to skip when listing shops.
_SKIP_ACCTNO = {"7TIK", "7LAZ01", "7LAZ02"}

# Known marketplace AR codes (name patterns alone miss some short ACCTNAME forms).
_KNOWN = {
    "shopee": {"7SPNT", "7SP", "7SICE", "7IAPS"},
    "lazada": {"7LAZ1", "7LAZ2", "7LPNT", "7LICE", "7IAPL"},
    "tiktok": {"7ICE"},
    "line": {"7LINE"},
}

_ARMAS_SHOPS = text(
    """
    SELECT
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname
    FROM dbo.ARMAS WITH (NOLOCK)
    WHERE LTRIM(RTRIM(ACCTNO)) LIKE '7%'
      AND COALESCE(CANCELED, 'N') <> 'Y'
    ORDER BY ACCTNO
    """
)

_ARMAS_ONE = text(
    """
    SELECT TOP 1
      LTRIM(RTRIM(ACCTNO)) AS acctno,
      LTRIM(RTRIM(ACCTNAME)) AS acctname,
      LTRIM(RTRIM(ADDR1)) AS addr1,
      LTRIM(RTRIM(ADDR2)) AS addr2,
      LTRIM(RTRIM(MOBILE)) AS tax_id
    FROM dbo.ARMAS WITH (NOLOCK)
    WHERE LTRIM(RTRIM(ACCTNO)) = :acct
    ORDER BY CASE WHEN COALESCE(CANCELED, 'N') = 'Y' THEN 1 ELSE 0 END, ID
    """
)


def _run(statement, params: dict | None = None):
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            return conn.execute(statement, params or {}).mappings().all()
    except Exception as exc:
        raise OnlineSaleError("kss", format_sql_error(exc, site="hq"), status=502) from exc


def detect_platform(acctname: str | None, acctno: str | None = None) -> str:
    name = (acctname or "").upper()
    code = (acctno or "").strip().upper()
    for platform, codes in _KNOWN.items():
        if code in codes:
            return platform
    if "SHOPEE" in name:
        return "shopee"
    if "LAZADA" in name:
        return "lazada"
    if "TIKTOK" in name or "TIK TOK" in name:
        return "tiktok"
    # LINE MY SHOP / Line Shopping — require LINE token, not bare 7L* customers.
    if re.search(r"\bLINE\b", name) or "LINE SHOP" in name or "LINE MY SHOP" in name:
        return "line"
    return ""


def shop_display_name(acctname: str | None) -> str:
    raw = re.sub(r"\s+", " ", (acctname or "").strip())
    raw = re.sub(r"^คุณลูกค้าทั่วไป\s+", "", raw, flags=re.IGNORECASE)
    match = re.fullmatch(r"(\S+)\s*\((.+)\)\s*", raw)
    if match:
        return re.sub(r"\s+", " ", match.group(2)).strip()
    return raw


def bill_acctname(platform: str, shop_name: str) -> str:
    """Stamp format used on recent TAD bills."""
    labels = {
        "shopee": "SHOPEE",
        "lazada": "LAZADA",
        "tiktok": "TIKTOK",
        "line": "LINE",
    }
    plat = labels.get(platform, platform.upper())
    shop = re.sub(r"\s+", " ", (shop_name or "").strip())
    return f"คุณลูกค้าทั่วไป {plat} ({shop})"[:60]


def list_platforms() -> list[dict[str, str]]:
    return [{"id": k, "label": label} for k, label in PLATFORMS]


def list_shops(platform: str) -> list[dict[str, Any]]:
    key = (platform or "").strip().lower()
    if key not in _PLATFORM_KEYS:
        raise OnlineSaleError("platform", "เลือกแพลตฟอร์ม Shopee / Lazada / TikTok / Line Shopping")
    rows = _run(_ARMAS_SHOPS)
    out: list[dict[str, Any]] = []
    for row in rows:
        acctno = str(row.get("acctno") or "").strip()
        acctname = str(row.get("acctname") or "").strip()
        if not acctno or acctno.upper() in _SKIP_ACCTNO:
            continue
        if detect_platform(acctname, acctno) != key:
            continue
        out.append(
            {
                "acctno": acctno,
                "acctname": acctname,
                "shop_name": shop_display_name(acctname),
                "platform": key,
                "remarks": PLATFORM_REMARKS[key],
            }
        )
    return out


def _join_address(addr1, addr2) -> str:
    parts: list[str] = []
    for raw in (addr1, addr2):
        text = str(raw or "").strip()
        if not text or text.upper() == "=DONE=":
            continue
        parts.append(text)
    return " ".join(parts)


def tax_id_digits(raw: str | None) -> str:
    """Return a 13-digit taxpayer id, or '' if not exactly 13 digits."""
    digits = re.sub(r"\D", "", raw or "")
    return digits if len(digits) == 13 else ""


def tax_id_from_remarks(remarks: str | None) -> str:
    """Match curated_kcw.fn_vat_tax_id: 13 digits after the last # in REMARKS.

    Marketplace TAD/CNTAD stamp e.g. ##0000000000001 (Lazada) — that value is
    what the VAT books and POS use as the buyer tax id.
    """
    text = str(remarks or "")
    tail = text.rsplit("#", 1)[-1] if "#" in text else text
    return tax_id_digits(tail)


def customer_name_without_shop(acctname: str | None) -> str:
    """คุณลูกค้าทั่วไป LAZADA (PNT TRACTOR) → คุณลูกค้าทั่วไป LAZADA."""
    raw = re.sub(r"\s+", " ", (acctname or "").strip())
    return re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()


def channel_label(platform: str | None, shop_name: str | None) -> str:
    """Lazada (PNT TRACTOR) — platform + shop on one line."""
    plat = {
        "shopee": "Shopee",
        "lazada": "Lazada",
        "tiktok": "TikTok",
        "line": "Line Shopping",
    }.get((platform or "").lower(), (platform or "").strip())
    shop = re.sub(r"\s+", " ", (shop_name or "").strip())
    if plat and shop:
        return f"{plat} ({shop})"
    return plat or shop


def party_from_armas(acctno: str) -> dict[str, str]:
    """Buyer block for print sheets: name / address / tax id from ARMAS."""
    code = (acctno or "").strip()
    if not code:
        return {"customer_name": "", "address": "", "tax_id": ""}
    rows = _run(_ARMAS_ONE, {"acct": code})
    if not rows:
        return {"customer_name": "", "address": "", "tax_id": ""}
    row = rows[0]
    return {
        "customer_name": str(row.get("acctname") or "").strip(),
        "address": _join_address(row.get("addr1"), row.get("addr2")),
        "tax_id": tax_id_digits(str(row.get("tax_id") or "")),
    }


def load_shop(acctno: str) -> dict[str, Any]:
    code = (acctno or "").strip()
    if not code:
        raise OnlineSaleError("shop", "เลือกร้านค้า")
    rows = _run(_ARMAS_ONE, {"acct": code})
    if not rows:
        raise OnlineSaleError("shop", f"ไม่พบบัญชีร้าน {code}")
    acctname = str(rows[0].get("acctname") or "").strip()
    platform = detect_platform(acctname, code)
    if not platform:
        raise OnlineSaleError("shop", f"บัญชี {code} ไม่ใช่ร้านออนไลน์")
    return {
        "acctno": code,
        "acctname": acctname,
        "shop_name": shop_display_name(acctname),
        "platform": platform,
        "remarks": PLATFORM_REMARKS[platform],
        "bill_acctname": bill_acctname(platform, shop_display_name(acctname)),
    }
