"""MAC address normalization helpers."""

from __future__ import annotations

import re

_MAC_RE = re.compile(
    r"^([0-9a-f]{2})([:-])([0-9a-f]{2})\2([0-9a-f]{2})\2([0-9a-f]{2})\2"
    r"([0-9a-f]{2})\2([0-9a-f]{2})$",
    re.IGNORECASE,
)


def normalize_mac(value: str) -> str:
    """Return lowercase ``aa:bb:cc:dd:ee:ff`` or raise ValueError."""
    text = (value or "").strip().lower().replace("-", ":")
    if not text:
        raise ValueError("MAC must not be empty")
    hex_only = re.sub(r"[^0-9a-f]", "", text)
    if len(hex_only) == 12 and not _MAC_RE.match(text):
        text = ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
    match = _MAC_RE.match(text)
    if not match:
        raise ValueError(f"invalid MAC address: {value!r}")
    return ":".join(match.group(i) for i in (1, 3, 4, 5, 6, 7))


def macs_equal(left: str, right: str) -> bool:
    try:
        return normalize_mac(left) == normalize_mac(right)
    except ValueError:
        return False
