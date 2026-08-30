from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings
from src.transfer.direction import ship_billno_prefix, receive_billno_prefix


class TransferWriteError(RuntimeError):
    def __init__(self, message: str, *, code: str = "transfer_write_failed"):
        super().__init__(message)
        self.code = code


def _next_billno_on_table(conn, table: str, prefix: str, when: datetime) -> str:
    yymm = when.strftime("%y%m")
    stem = f"{prefix}{yymm}-"
    row = conn.execute(
        text(
            f"""
            SELECT MAX(BILLNO) AS max_no
            FROM dbo.{table}
            WHERE BILLNO LIKE :pat
            """
        ),
        {"pat": stem + "%"},
    ).mappings().first()
    max_no = (row or {}).get("max_no") or ""
    seq = 1
    if max_no and "-" in str(max_no):
        tail = str(max_no).rsplit("-", 1)[-1]
        try:
            seq = int(tail) + 1
        except ValueError:
            seq = 1
    candidate = f"{stem}{seq:05d}"
    if len(candidate) > 15:
        candidate = f"{stem}{seq:04d}"
    if len(candidate) > 15:
        raise TransferWriteError("generated BILLNO exceeds 15 chars", code="billno_overflow")
    return candidate


def next_simas_billno(conn, *, from_branch: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    prefix = ship_billno_prefix(from_branch=from_branch)
    return _next_billno_on_table(conn, "SIMAS", prefix, when)


def next_pimas_billno(
    conn, *, from_branch: str, to_branch: str, when: datetime | None = None
) -> str:
    when = when or datetime.now()
    prefix = receive_billno_prefix(from_branch=from_branch, to_branch=to_branch)
    return _next_billno_on_table(conn, "PIMAS", prefix, when)


def writer_engine_for_branch(branch: str) -> Engine:
    site = (branch or "HQ").strip().lower()
    if site == "syp":
        return get_site_engine("syp")
    return get_site_engine("hq")


def _fetch_icmas_row(conn, bcode: str) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT MCODE, PCODE, UI1, LOCATION1, QTYOH2
            FROM dbo.ICMAS
            WHERE LTRIM(RTRIM(BCODE)) = :bcode
            """
        ),
        {"bcode": bcode},
    ).mappings().first()
    return dict(row) if row else None
