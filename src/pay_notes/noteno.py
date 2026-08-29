from __future__ import annotations

import re

NOTENO_MAX_LEN = 15
_SUFFIX_RE = re.compile(r"^(.+)_(\d+)$")


def display_noteno(stored: str) -> str:
    """Strip auto suffix (_1) for operator-facing labels."""
    s = (stored or "").strip()
    m = _SUFFIX_RE.match(s)
    return m.group(1) if m else s


def parse_noteno_suffix(stored: str) -> tuple[str, int | None]:
    s = (stored or "").strip()
    m = _SUFFIX_RE.match(s)
    if m:
        return m.group(1), int(m.group(2))
    return s, None


def format_suffixed_noteno(bare: str, suffix: int) -> str:
    candidate = f"{bare.strip()}_{suffix}"
    if len(candidate) > NOTENO_MAX_LEN:
        raise ValueError(f"NOTENO too long ({len(candidate)} > {NOTENO_MAX_LEN}): {candidate!r}")
    return candidate
