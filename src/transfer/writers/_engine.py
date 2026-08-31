from __future__ import annotations

import threading
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.db.mssql_host import pick_mssql_server, tcp_open
from src.parts9_explorer.db import get_site_engine
from src.transfer.config import get_transfer_settings
from src.transfer.direction import receive_billno_prefix, ship_billno_prefix

_writer_engines: dict[str, Engine] = {}
_writer_engines_lock = threading.Lock()


class TransferWriteError(RuntimeError):
    def __init__(self, message: str, *, code: str = "transfer_write_failed"):
        super().__init__(message)
        self.code = code


def transfer_bill_yymm(when: datetime) -> str:
    """YYMM for TF/3TF bills — Buddhist era (2569 → 69), same as PARTS9 pay vouchers."""
    yy = (when.year + 543) % 100
    return f"{yy:02d}{when.month:02d}"


def _next_billno_on_table(conn, table: str, prefix: str, when: datetime) -> str:
    yymm = transfer_bill_yymm(when)
    stem = f"{prefix}{yymm}-"
    row = conn.execute(
        text(
            f"""
            SELECT MAX(
              TRY_CAST(
                SUBSTRING(
                  LTRIM(RTRIM(CONVERT(nvarchar(40), BILLNO))),
                  LEN(:stem) + 1,
                  40
                ) AS int
              )
            ) AS max_seq
            FROM dbo.{table}
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), BILLNO))) LIKE :pat
            """
        ),
        {"pat": stem + "%", "stem": stem},
    ).mappings().first()
    max_seq = (row or {}).get("max_seq")
    try:
        seq = int(max_seq) + 1 if max_seq is not None else 1
    except (TypeError, ValueError):
        seq = 1
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


def _writer_odbc_url(*, site: str) -> str:
    settings = get_transfer_settings()
    if not settings.pos_mssql_writer_username:
        raise TransferWriteError(
            "POS_MSSQL_WRITER_USERNAME not configured",
            code="writer_not_configured",
        )
    if site == "syp":
        server = (settings.parts9_syp_server or "kss-pc").split(",")[0].strip() or "kss-pc"
        database = settings.parts9_syp_database or "PARTS9"
    else:
        server = (settings.pos_mssql_server or "KSS").split(",")[0].strip() or "KSS"
        database = settings.pos_mssql_database or "PARTS9"
    picked = pick_mssql_server(server)
    if not tcp_open(picked):
        raise ConnectionError("SQL Server port 1433 not reachable on %s" % picked)
    odbc = (
        f"DRIVER={{{settings.pos_mssql_driver}}};"
        f"SERVER={picked};"
        f"DATABASE={database};"
        f"UID={settings.pos_mssql_writer_username};"
        f"PWD={settings.pos_mssql_writer_password};"
        "TrustServerCertificate=yes;"
        "Connection Timeout=8;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


def writer_engine_for_branch(branch: str) -> Engine:
    site = (branch or "HQ").strip().lower()
    if site not in ("hq", "syp"):
        site = "hq"
    with _writer_engines_lock:
        existing = _writer_engines.get(site)
        if existing is not None:
            return existing
    engine = create_engine(
        _writer_odbc_url(site=site),
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=8,
        connect_args={"timeout": 8},
    )
    with _writer_engines_lock:
        existing = _writer_engines.get(site)
        if existing is not None:
            try:
                engine.dispose()
            except Exception:
                pass
            return existing
        _writer_engines[site] = engine
        return engine


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
