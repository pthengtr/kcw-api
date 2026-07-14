from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_CSV_PATH = (
    r"G:\Shared drives\KCW-Data\kcw_analytics\01_raw\raw_hq_simas_sales_bills.csv"
)


class CompanionBillSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    # mock | csv | mssql
    pos_bill_source: str = Field(default="mock", validation_alias="POS_BILL_SOURCE")
    pos_bills_csv_path: str = Field(
        default=DEFAULT_CSV_PATH,
        validation_alias="POS_BILLS_CSV_PATH",
    )
    # latest = newest N matching rows (testing)
    # today = only today's bills (production-shaped)
    pos_bills_mode: str = Field(default="latest", validation_alias="POS_BILLS_MODE")
    pos_bills_limit: int = Field(default=10, validation_alias="POS_BILLS_LIMIT")

    # Local SIMAS / SQL Server (used when POS_BILL_SOURCE=mssql)
    pos_mssql_server: str = Field(default="KSS", validation_alias="POS_MSSQL_SERVER")
    pos_mssql_database: str = Field(default="PARTS9", validation_alias="POS_MSSQL_DATABASE")
    pos_mssql_username: str = Field(default="python_reader", validation_alias="POS_MSSQL_USERNAME")
    pos_mssql_password: str = Field(default="", validation_alias="POS_MSSQL_PASSWORD")
    pos_mssql_driver: str = Field(
        default="ODBC Driver 17 for SQL Server",
        validation_alias="POS_MSSQL_DRIVER",
    )
    # Example: dbo.SalesBills  (set to your real bill-header table/view)
    pos_mssql_bills_table: str = Field(default="", validation_alias="POS_MSSQL_BILLS_TABLE")

    @field_validator("pos_bill_source", "pos_bills_mode")
    @classmethod
    def normalize_choice(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator(
        "pos_bills_csv_path",
        "pos_mssql_server",
        "pos_mssql_database",
        "pos_mssql_username",
        "pos_mssql_password",
        "pos_mssql_driver",
        "pos_mssql_bills_table",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip().strip('"').strip("'")

    @field_validator("pos_bills_limit")
    @classmethod
    def positive_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value


@lru_cache
def get_companion_bill_settings() -> CompanionBillSettings:
    return CompanionBillSettings()
