from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

_BKK = ZoneInfo("Asia/Bangkok")
NOTENO_MAX_LEN = 15


def buddhist_yymm(when: datetime | None = None) -> str:
    dt = when or datetime.now(_BKK)
    yy = (dt.year + 543) % 100
    return f"{yy:02d}{dt.month:02d}"


def note_stem(jourmode: str, when: datetime | None = None) -> str:
    """VAT (JOURMODE=1) → BN… ; Non-VAT (JOURMODE=2) → BNN…"""
    yymm = buddhist_yymm(when)
    mode = (jourmode or "1").strip() or "1"
    if mode == "2":
        return f"BNN{yymm}-"
    return f"BN{yymm}-"


def next_noteno(conn, *, jourmode: str, when: datetime | None = None) -> str:
    stem = note_stem(jourmode, when)
    row = conn.execute(
        text("SELECT MAX(NOTENO) AS max_no FROM dbo.RVMAS WHERE NOTENO LIKE :pat"),
        {"pat": stem + "%"},
    ).mappings().first()
    max_no = (row or {}).get("max_no") or ""
    seq = 1
    if max_no and "-" in str(max_no):
        try:
            seq = int(str(max_no).rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    candidate = f"{stem}{seq:03d}"
    if len(candidate) > NOTENO_MAX_LEN:
        raise ValueError(f"NOTENO exceeds {NOTENO_MAX_LEN} chars: {candidate}")
    return candidate
