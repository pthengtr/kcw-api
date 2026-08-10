"""Deterministic contract for product-scan LIFF ↔ LINE chatbot.

Callback message format (sent via liff.sendMessages from kcw-v2):
  📦 สแกนสินค้า: <barcode>

Keep parsing deterministic — never send this through general AI routing.
"""

from __future__ import annotations

import re

# Canonical prefix used by kcw-v2 when sending the scan result back into chat.
PRODUCT_SCAN_CALLBACK_PREFIX = "📦 สแกนสินค้า:"

# Accept a no-emoji variant for resilience (manual paste / older clients).
_CALLBACK_PREFIXES = (
    PRODUCT_SCAN_CALLBACK_PREFIX,
    "สแกนสินค้า:",
)

# Compact command aliases (whitespace stripped, lowercased for Latin).
PRODUCT_SCAN_COMMANDS = {
    "สแกน",
    "สแกนสินค้า",
    "สแกนบาร์โค้ด",
    "สแกนบาร์โคด",
    "scan",
    "scanproduct",
    "scanbarcode",
    "scan product",
    "scan barcode",
}

_BARCODE_RE = re.compile(r"^[A-Za-z0-9\-_.]{1,64}$")


def format_product_scan_callback(barcode: str) -> str:
    """Build the LINE text message LIFF should send after a successful scan."""
    code = sanitize_barcode(barcode)
    if not code:
        raise ValueError("Invalid barcode for product scan callback")
    return f"{PRODUCT_SCAN_CALLBACK_PREFIX} {code}"


def sanitize_barcode(raw: str | None) -> str | None:
    """Validate/sanitize a scanned barcode/SKU value."""
    if raw is None:
        return None
    # Code 39 sometimes wraps values with *; strip those only.
    code = str(raw).strip().strip("*").strip()
    if not code:
        return None
    # Reject control / whitespace / emoji clutter inside the code itself.
    if not _BARCODE_RE.fullmatch(code):
        return None
    return code


def _match_callback_prefix(text: str | None) -> str | None:
    """Return the matched prefix if this looks like a LIFF scan callback."""
    t = (text or "").strip()
    if not t:
        return None
    for prefix in _CALLBACK_PREFIXES:
        if t.startswith(prefix):
            return prefix
    return None


def is_product_scan_callback(text: str | None) -> bool:
    """True when the message uses the LIFF scan-callback prefix (even if barcode is bad)."""
    return _match_callback_prefix(text) is not None


def parse_product_scan_callback(text: str | None) -> str | None:
    """Extract a sanitized barcode from a LIFF callback, or None if missing/invalid."""
    prefix = _match_callback_prefix(text)
    if prefix is None:
        return None
    return sanitize_barcode((text or "").strip()[len(prefix) :])


def is_product_scan_command(text: str | None) -> bool:
    """True when the user is asking to open the product scanner LIFF."""
    t = (text or "").strip()
    if not t:
        return False

    # Callbacks must never be treated as open-scanner commands.
    if is_product_scan_callback(t):
        return False

    compact = "".join(t.lower().split())
    aliases = {"".join(a.lower().split()) for a in PRODUCT_SCAN_COMMANDS}
    return compact in aliases
