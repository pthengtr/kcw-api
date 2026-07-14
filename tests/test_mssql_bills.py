from decimal import Decimal
from unittest.mock import MagicMock
from urllib.parse import unquote_plus

import pandas as pd
import pytest

from src.companion.config import CompanionBillSettings
from src.companion.mssql_bills import (
    _quote_table_name,
    build_mssql_odbc_url,
    get_mssql_bill,
    list_mssql_bills,
)


def _settings(**overrides) -> CompanionBillSettings:
    base = {
        "pos_bill_source": "mssql",
        "pos_bills_mode": "latest",
        "pos_bills_limit": 2,
        "pos_mssql_server": "KSS",
        "pos_mssql_database": "PARTS9",
        "pos_mssql_username": "python_reader",
        "pos_mssql_password": "secret",
        "pos_mssql_bills_table": "dbo.SalesBills",
    }
    base.update(overrides)
    return CompanionBillSettings(**base)


def test_quote_table_name():
    assert _quote_table_name("dbo.SalesBills") == "[dbo].[SalesBills]"
    assert _quote_table_name("SalesBills") == "[SalesBills]"
    with pytest.raises(ValueError):
        _quote_table_name("dbo.;DROP TABLE x")


def test_build_mssql_odbc_url_matches_notebook_pattern():
    url = build_mssql_odbc_url(_settings())
    assert url.startswith("mssql+pyodbc:///?odbc_connect=")
    odbc = unquote_plus(url.split("odbc_connect=", 1)[1])
    assert "DRIVER={ODBC Driver 17 for SQL Server};" in odbc
    assert "SERVER=KSS;" in odbc
    assert "DATABASE=PARTS9;" in odbc
    assert "UID=python_reader;" in odbc
    assert "PWD=secret;" in odbc
    assert "TrustServerCertificate=yes;" in odbc


def test_list_mssql_bills_uses_sql_and_maps_rows():
    frame = pd.DataFrame(
        [
            {
                "ID": "101",
                "BILLNO": "B2607140001",
                "AFTERTAX": "250.00",
                "BILLDATE": "2026-07-14",
                "BILLTIME": "09:15:00",
                "PAID": "N",
                "CASHED": "Y",
                "SALE": "alice",
            },
            {
                "ID": "106",
                "BILLNO": "TF2607140006",
                "AFTERTAX": "77.00",
                "BILLDATE": "2026-07-14",
                "BILLTIME": "14:00:00",
                "PAID": "N",
                "CASHED": "Y",
                "SALE": "frank",
            },
        ]
    )
    engine = MagicMock()
    import src.companion.mssql_bills as mssql_bills

    original = mssql_bills.pd.read_sql
    mocked = MagicMock(return_value=frame)
    mssql_bills.pd.read_sql = mocked
    try:
        bills = list_mssql_bills(_settings(), engine=engine)
    finally:
        mssql_bills.pd.read_sql = original

    assert len(bills) == 1
    assert bills[0].bill_number == "B2607140001"
    assert bills[0].amount == Decimal("250.00")
    assert bills[0].salesperson == "alice"
    sql_text = str(mocked.call_args.args[0])
    assert "NOT LIKE 'TF%'" in sql_text
    assert "CASHED" in sql_text
    assert "[dbo].[SalesBills]" in sql_text
    assert "GETDATE()" not in sql_text


def test_list_mssql_bills_today_mode_filters_on_server():
    import src.companion.mssql_bills as mssql_bills

    original = mssql_bills.pd.read_sql
    mocked = MagicMock(return_value=pd.DataFrame())
    mssql_bills.pd.read_sql = mocked
    try:
        list_mssql_bills(_settings(pos_bills_mode="today"), engine=MagicMock())
    finally:
        mssql_bills.pd.read_sql = original

    sql_text = str(mocked.call_args.args[0])
    assert "GETDATE()" in sql_text
    assert "CONVERT(date, [BILLDATE])" in sql_text


def test_get_mssql_bill():
    frame = pd.DataFrame(
        [
            {
                "ID": "103",
                "BILLNO": "B2607120003",
                "AFTERTAX": "1250.00",
                "BILLDATE": "2026-07-12",
                "BILLTIME": "11:40:00",
                "PAID": "Y",
                "CASHED": "Y",
                "SALE": "carol",
            }
        ]
    )
    import src.companion.mssql_bills as mssql_bills

    original = mssql_bills.pd.read_sql
    mssql_bills.pd.read_sql = MagicMock(return_value=frame)
    try:
        bill = get_mssql_bill("103", _settings(), engine=MagicMock())
    finally:
        mssql_bills.pd.read_sql = original

    assert bill is not None
    assert bill.bill_number == "B2607120003"
    assert bill.pos_status == "Y"
