"""Validate / sanitize scanned barcode or SKU values."""

from __future__ import annotations

import re

_BARCODE_RE = re.compile(r"^[A-Za-z0-9\-_.]{1,64}$")


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
