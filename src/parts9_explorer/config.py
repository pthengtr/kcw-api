from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Parts9ExplorerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    parts9_explorer_enabled: bool = Field(default=True, validation_alias="PARTS9_EXPLORER_ENABLED")
    parts9_explorer_site: str = Field(default="HQ", validation_alias="PARTS9_EXPLORER_SITE")
    parts9_explorer_listen_port: int = Field(default=8788, validation_alias="PARTS9_EXPLORER_LISTEN_PORT")
    parts9_explorer_public_base_url: str = Field(default="", validation_alias="PARTS9_EXPLORER_PUBLIC_BASE_URL")
    parts9_explorer_token_secret: str = Field(default="", validation_alias="PARTS9_EXPLORER_TOKEN_SECRET")
    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")
    stock_check_token_ttl_seconds: int = Field(default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS")

    pos_mssql_server: str = Field(default="KSS", validation_alias="POS_MSSQL_SERVER")
    pos_mssql_database: str = Field(default="PARTS9", validation_alias="POS_MSSQL_DATABASE")
    pos_mssql_username: str = Field(default="python_reader", validation_alias="POS_MSSQL_USERNAME")
    pos_mssql_password: str = Field(default="", validation_alias="POS_MSSQL_PASSWORD")
    pos_mssql_driver: str = Field(default="ODBC Driver 18 for SQL Server", validation_alias="POS_MSSQL_DRIVER")
    # Optional dedicated HQ PARTS9 host (analytic-compatible). Empty → POS_MSSQL_*.
    # SYP boxes must set this to a reachable HQ host OR rely on transfer peer stock —
    # do not leave POS_MSSQL pointing at kss-pc and expect get_site_engine("hq") to be HQ.
    parts9_hq_server: str = Field(default="", validation_alias="PARTS9_HQ_SERVER")
    parts9_hq_database: str = Field(default="", validation_alias="PARTS9_HQ_DATABASE")
    parts9_syp_server: str = Field(default="kss-pc", validation_alias="PARTS9_SYP_SERVER")
    parts9_syp_database: str = Field(default="PARTS9", validation_alias="PARTS9_SYP_DATABASE")

    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_image_bucket: str = Field(default="pictures", validation_alias="SUPABASE_IMAGE_BUCKET")
    supabase_image_base_folder: str = Field(default="product", validation_alias="SUPABASE_IMAGE_BASE_FOLDER")

    @property
    def token_secret(self) -> str:
        return (self.parts9_explorer_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def site(self) -> str:
        return (self.parts9_explorer_site or "HQ").strip().upper() or "HQ"


@lru_cache
def get_explorer_settings() -> Parts9ExplorerSettings:
    return Parts9ExplorerSettings()
