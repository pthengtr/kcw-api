"""Backward-compatible re-exports.

Prefer `src.barcode` and `src.handlers.product_scan` for new code.
LIFF product scanning has been replaced by LINE camera / photo upload.
"""

from src.barcode.sanitize import sanitize_barcode
from src.handlers.product_scan import (
    PRODUCT_SCAN_COMMANDS,
    is_product_scan_callback,
    is_product_scan_command,
    parse_product_scan_callback,
)

PRODUCT_SCAN_CALLBACK_PREFIX = "📦 สแกนสินค้า:"


def format_product_scan_callback(barcode: str) -> str:
    code = sanitize_barcode(barcode)
    if not code:
        raise ValueError("Invalid barcode for product scan callback")
    return f"{PRODUCT_SCAN_CALLBACK_PREFIX} {code}"


__all__ = [
    "PRODUCT_SCAN_CALLBACK_PREFIX",
    "PRODUCT_SCAN_COMMANDS",
    "format_product_scan_callback",
    "is_product_scan_callback",
    "is_product_scan_command",
    "parse_product_scan_callback",
    "sanitize_barcode",
]
