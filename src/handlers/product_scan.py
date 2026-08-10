"""Product scan LIFF launch + callback handling for the LINE bot."""

from __future__ import annotations

import os

from src.handlers.check import handle_check_response
from src.liff.product_scan_contract import (
    is_product_scan_callback as _is_callback,
    is_product_scan_command as _is_command,
    parse_product_scan_callback,
)

# Full LIFF URL, e.g. https://liff.line.me/1234567890-abcdefgh
KCW_LIFF_PRODUCT_SCANNER_URL = os.getenv("KCW_LIFF_PRODUCT_SCANNER_URL", "").strip()


def is_product_scan_command(text: str) -> bool:
    return _is_command(text)


def is_product_scan_callback(text: str) -> bool:
    return _is_callback(text)


def _build_scanner_uri() -> str | None:
    url = KCW_LIFF_PRODUCT_SCANNER_URL
    if not url:
        return None
    if not (url.startswith("https://") or url.startswith("http://")):
        return None
    return url


def handle_product_scan_command() -> dict:
    """Reply with a button that opens the LIFF product scanner (Reply API)."""
    uri = _build_scanner_uri()
    if not uri:
        return {
            "type": "text",
            "text": (
                "ระบบสแกนสินค้ายังไม่ได้ตั้งค่าครับ\n"
                "กรุณาตั้งค่า KCW_LIFF_PRODUCT_SCANNER_URL แล้วลองใหม่"
            ),
        }

    # Buttons template URI action — free Reply API, no Push.
    # Label max length for buttons template is 20 chars (Unicode-aware on LINE).
    return {
        "type": "messages",
        "messages": [
            {
                "type": "template",
                "altText": "สแกนสินค้า — กดปุ่มเพื่อเปิดกล้อง",
                "template": {
                    "type": "buttons",
                    "text": (
                        "กดปุ่มเพื่อเปิดกล้องสแกนบาร์โค้ดสินค้า\n"
                        "หลังสแกน ระบบจะส่งรหัสกลับมาที่แชทนี้ให้อัตโนมัติ"
                    ),
                    "actions": [
                        {
                            "type": "uri",
                            "label": "สแกนสินค้า",
                            "uri": uri,
                        }
                    ],
                },
            }
        ],
    }


def handle_product_scan_callback(engine, user_text: str) -> dict:
    """Parse LIFF callback and reuse existing product check lookup."""
    barcode = parse_product_scan_callback(user_text)
    if not barcode:
        return {
            "type": "text",
            "text": (
                "อ่านรหัสจากสแกนไม่สำเร็จครับ\n"
                "กรุณาพิมพ์ สแกนสินค้า แล้วลองใหม่"
            ),
        }

    # Reuse the existing เช็ค {bcode} path — same Reply API response style.
    return handle_check_response(engine, f"เช็ค {barcode}")
