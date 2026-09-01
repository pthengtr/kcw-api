from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TransferSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    transfer_enabled: bool = Field(default=True, validation_alias="TRANSFER_ENABLED")
    transfer_site: str = Field(default="HQ", validation_alias="TRANSFER_SITE")
    transfer_listen_port: int = Field(default=8792, validation_alias="TRANSFER_LISTEN_PORT")
    transfer_public_base_url: str = Field(default="", validation_alias="TRANSFER_PUBLIC_BASE_URL")
    transfer_tailscale_base_url: str = Field(
        default="", validation_alias="TRANSFER_TAILSCALE_BASE_URL"
    )
    # Peer kcw-transfer base (no trailing slash) for remote-site ICMAS when SQL is unreachable.
    # SYP → HQ stock: http://hq-ubuntu-server:8792 (Tailscale). HQ usually keeps direct kss-pc SQL.
    transfer_peer_base_url: str = Field(default="", validation_alias="TRANSFER_PEER_BASE_URL")
    transfer_token_secret: str = Field(default="", validation_alias="TRANSFER_TOKEN_SECRET")
    transfer_hq_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_HQ_WRITE_ENABLED"
    )
    transfer_hq_ship_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_HQ_SHIP_WRITE_ENABLED"
    )
    transfer_syp_ship_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_SYP_SHIP_WRITE_ENABLED"
    )
    transfer_hq_receive_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_HQ_RECEIVE_WRITE_ENABLED"
    )
    transfer_syp_receive_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_SYP_RECEIVE_WRITE_ENABLED"
    )
    transfer_syp_write_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_SYP_WRITE_ENABLED"
    )
    transfer_iclow_stamp_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_ICLOW_STAMP_ENABLED"
    )
    transfer_syp_receive_enabled: bool = Field(
        default=False, validation_alias="TRANSFER_SYP_RECEIVE_ENABLED"
    )
    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")

    @property
    def hq_ship_write_enabled(self) -> bool:
        return self.transfer_hq_ship_write_enabled or self.transfer_hq_write_enabled

    @property
    def syp_ship_write_enabled(self) -> bool:
        return self.transfer_syp_ship_write_enabled or self.transfer_syp_write_enabled

    @property
    def hq_receive_write_enabled(self) -> bool:
        return self.transfer_hq_receive_write_enabled

    @property
    def syp_receive_write_enabled(self) -> bool:
        return self.transfer_syp_receive_write_enabled or self.transfer_syp_receive_enabled

    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )

    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY")

    pos_mssql_username: str = Field(default="", validation_alias="POS_MSSQL_USERNAME")
    pos_mssql_password: str = Field(default="", validation_alias="POS_MSSQL_PASSWORD")
    pos_mssql_writer_username: str = Field(
        default="", validation_alias="POS_MSSQL_WRITER_USERNAME"
    )
    pos_mssql_writer_password: str = Field(
        default="", validation_alias="POS_MSSQL_WRITER_PASSWORD"
    )
    pos_mssql_server: str = Field(default="KSS", validation_alias="POS_MSSQL_SERVER")
    pos_mssql_database: str = Field(default="PARTS9", validation_alias="POS_MSSQL_DATABASE")
    parts9_hq_server: str = Field(default="", validation_alias="PARTS9_HQ_SERVER")
    parts9_hq_database: str = Field(default="", validation_alias="PARTS9_HQ_DATABASE")
    parts9_syp_server: str = Field(default="kss-pc", validation_alias="PARTS9_SYP_SERVER")
    parts9_syp_database: str = Field(default="PARTS9", validation_alias="PARTS9_SYP_DATABASE")
    pos_mssql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server", validation_alias="POS_MSSQL_DRIVER"
    )

    @property
    def token_secret(self) -> str:
        return (self.transfer_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def site(self) -> str:
        return (self.transfer_site or "HQ").strip().upper() or "HQ"

    @property
    def is_syp(self) -> bool:
        return self.site == "SYP"

    @property
    def is_hq(self) -> bool:
        return self.site == "HQ"

    @property
    def peer_base_url(self) -> str:
        explicit = (self.transfer_peer_base_url or "").strip().rstrip("/")
        if explicit:
            return explicit
        # Tailscale MagicDNS defaults — both boxes already expose :8792 on the tailnet.
        if self.is_syp:
            return "http://hq-ubuntu-server:8792"
        return "http://syp-ubuntu-server:8792"


@lru_cache
def get_transfer_settings() -> TransferSettings:
    return TransferSettings()
