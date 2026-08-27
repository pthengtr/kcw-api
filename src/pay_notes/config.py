from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PayNotesSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pay_notes_enabled: bool = Field(default=True, validation_alias="PAY_NOTES_ENABLED")
    pay_notes_site: str = Field(default="HQ", validation_alias="PAY_NOTES_SITE")
    pay_notes_listen_port: int = Field(default=8791, validation_alias="PAY_NOTES_LISTEN_PORT")
    pay_notes_public_base_url: str = Field(default="", validation_alias="PAY_NOTES_PUBLIC_BASE_URL")
    pay_notes_tailscale_base_url: str = Field(
        default="", validation_alias="PAY_NOTES_TAILSCALE_BASE_URL"
    )
    pay_notes_token_secret: str = Field(default="", validation_alias="PAY_NOTES_TOKEN_SECRET")
    pay_notes_write_enabled: bool = Field(default=False, validation_alias="PAY_NOTES_WRITE_ENABLED")

    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )

    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_image_bucket: str = Field(default="pictures", validation_alias="SUPABASE_IMAGE_BUCKET")

    pos_mssql_writer_username: str = Field(default="", validation_alias="POS_MSSQL_WRITER_USERNAME")
    pos_mssql_writer_password: str = Field(default="", validation_alias="POS_MSSQL_WRITER_PASSWORD")

    @property
    def token_secret(self) -> str:
        return (self.pay_notes_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def site(self) -> str:
        return (self.pay_notes_site or "HQ").strip().upper() or "HQ"


@lru_cache
def get_pay_notes_settings() -> PayNotesSettings:
    return PayNotesSettings()
