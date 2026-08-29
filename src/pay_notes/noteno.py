from __future__ import annotations

import re
from typing import Any

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


def noteno_meta(stored: str) -> dict[str, Any]:
    """Operator-facing labels for auto-suffixed KSS NOTENO values."""
    note = (stored or "").strip()
    bare, suffix = parse_noteno_suffix(note)
    if suffix is None:
        bare = display_noteno(note)
    reused = suffix is not None
    reuse_round = suffix + 1 if suffix is not None else 1
    return {
        "noteno_display": bare,
        "noteno_suffix": suffix,
        "is_reused_label": reused,
        "reuse_round": reuse_round,
        "reuse_badge": f"ใช้ซ้ำ·รอบ {reuse_round}" if reused else "",
        "reuse_hint": (
            f"เลขใบวางบิล {bare} เคยถูกใช้ใน KSS แล้ว "
            f"ระบบบันทึกเป็น {note} (รอบที่ {reuse_round})"
            if reused
            else ""
        ),
    }
