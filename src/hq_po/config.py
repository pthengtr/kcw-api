from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HqPoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hq_po_enabled: bool = Field(default=True, validation_alias="HQ_PO_ENABLED")
    hq_po_listen_port: int = Field(default=8793, validation_alias="HQ_PO_LISTEN_PORT")
    hq_po_public_base_url: str = Field(default="", validation_alias="HQ_PO_PUBLIC_BASE_URL")
    hq_po_tailscale_base_url: str = Field(
        default="", validation_alias="HQ_PO_TAILSCALE_BASE_URL"
    )
    hq_po_iclow_stamp_enabled: bool = Field(
        default=False, validation_alias="HQ_PO_ICLOW_STAMP_ENABLED"
    )
    hq_po_token_secret: str = Field(default="", validation_alias="HQ_PO_TOKEN_SECRET")
    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY")

    @property
    def token_secret(self) -> str:
        return (self.hq_po_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def stamp_enabled(self) -> bool:
        return bool(self.hq_po_iclow_stamp_enabled)


@lru_cache
def get_hq_po_settings() -> HqPoSettings:
    return HqPoSettings()
