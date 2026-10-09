from __future__ import annotations

from datetime import date
from uuid import uuid4


def buddhist_yymm(on: date | None = None) -> str:
    day = on or date.today()
    return f"{(day.year + 543) % 100:02d}{day.month:02d}"


def make_short_id() -> str:
    return uuid4().hex[:8].upper()


def make_docno(short_id: str, on: date | None = None) -> str:
    """HP + Buddhist YYMM + 4 hex chars. Does not collide with PARTS9 POYYMM-NNN."""
    token = (short_id or "").replace("-", "").strip().upper()
    if len(token) < 4:
        token = (token + "XXXX")[:4]
    return f"HP{buddhist_yymm(on)}-{token[:4]}"
