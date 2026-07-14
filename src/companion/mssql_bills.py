from __future__ import annotations

import logging
import re
from functools import lru_cache
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.companion.bill_mapping import REQUIRED_COLUMNS, frames_to_bills, row_to_bill
from src.companion.bills import PosBill
from src.companion.config import CompanionBillSettings, get_companion_bill_settings

logger = logging.getLogger("kcw.companion.mssql_bills")

_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _quote_table_name(table_name: str) -> str:
    cleaned = table_name.strip().strip("[]")
    if not _TABLE_RE.fullmatch(cleaned):
        raise ValueError(
            "POS_MSSQL_BILLS_TABLE must look like TableName or schema.TableName"
        )
    return ".".join(f"[{part}]" for part in cleaned.split("."))


def build_mssql_odbc_url(settings: CompanionBillSettings) -> str:
    driver = settings.pos_mssql_driver
    odbc_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={settings.pos_mssql_server};"
        f"DATABASE={settings.pos_mssql_database};"
        f"UID={settings.pos_mssql_username};"
        f"PWD={settings.pos_mssql_password};"
        "TrustServerCertificate=yes;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_str)


@lru_cache(maxsize=1)
def get_mssql_engine() -> Engine:
    settings = get_companion_bill_settings()
    if not settings.pos_mssql_server or not settings.pos_mssql_database:
        raise ValueError("POS_MSSQL_SERVER and POS_MSSQL_DATABASE are required")
    if not settings.pos_mssql_username:
        raise ValueError("POS_MSSQL_USERNAME is required")
    if not settings.pos_mssql_password:
        raise ValueError("POS_MSSQL_PASSWORD is required when POS_BILL_SOURCE=mssql")
    return create_engine(build_mssql_odbc_url(settings), pool_pre_ping=True)


def clear_mssql_engine_cache() -> None:
    get_mssql_engine.cache_clear()


def _select_columns_sql() -> str:
    # Same shape as the SIMAS CSV export; SALE is optional at the app layer
    # but expected on the bill-header table/view (NULL is fine).
    cols = list(REQUIRED_COLUMNS) + ["SALE"]
    return ", ".join(f"[{c}]" for c in cols)


def _base_where_sql(*, today_only: bool) -> str:
    clauses = [
        "UPPER(LTRIM(RTRIM(COALESCE([CASHED], '')))) = 'Y'",
        "UPPER(LTRIM(RTRIM(COALESCE([BILLNO], '')))) NOT LIKE 'TF%'",
    ]
    if today_only:
        # Assumes SQL Server local clock matches shop timezone (Thailand).
        clauses.append("CONVERT(date, [BILLDATE]) = CONVERT(date, GETDATE())")
    return " AND ".join(clauses)


def list_mssql_bills(
    settings: CompanionBillSettings | None = None,
    *,
    engine: Engine | None = None,
) -> list[PosBill]:
    settings = settings or get_companion_bill_settings()
    if not settings.pos_mssql_bills_table:
        raise ValueError("POS_MSSQL_BILLS_TABLE is required when POS_BILL_SOURCE=mssql")

    table_sql = _quote_table_name(settings.pos_mssql_bills_table)
    today_only = settings.pos_bills_mode == "today"
    limit = int(settings.pos_bills_limit)

    sql = text(
        f"""
        SELECT TOP ({limit})
            {_select_columns_sql()}
        FROM {table_sql}
        WHERE {_base_where_sql(today_only=today_only)}
        ORDER BY [BILLDATE] DESC, [BILLTIME] DESC
        """
    )

    eng = engine or get_mssql_engine()
    frame = pd.read_sql(sql, eng)
    if frame.empty:
        return []
    return frames_to_bills(frame)


def get_mssql_bill(
    pos_bill_id: str,
    settings: CompanionBillSettings | None = None,
    *,
    engine: Engine | None = None,
) -> PosBill | None:
    settings = settings or get_companion_bill_settings()
    if not settings.pos_mssql_bills_table:
        raise ValueError("POS_MSSQL_BILLS_TABLE is required when POS_BILL_SOURCE=mssql")

    table_sql = _quote_table_name(settings.pos_mssql_bills_table)
    sql = text(
        f"""
        SELECT TOP (1)
            {_select_columns_sql()}
        FROM {table_sql}
        WHERE {_base_where_sql(today_only=False)}
          AND LTRIM(RTRIM(CONVERT(varchar(64), [ID]))) = :pos_bill_id
        """
    )
    eng = engine or get_mssql_engine()
    frame = pd.read_sql(sql, eng, params={"pos_bill_id": str(pos_bill_id).strip()})
    if frame.empty:
        return None
    return row_to_bill(frame.iloc[0])
