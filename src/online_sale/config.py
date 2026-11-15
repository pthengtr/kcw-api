from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OnlineSaleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    online_sale_enabled: bool = Field(default=True, validation_alias="ONLINE_SALE_ENABLED")
    online_sale_listen_port: int = Field(
        default=8796, validation_alias="ONLINE_SALE_LISTEN_PORT"
    )
    online_sale_public_base_url: str = Field(
        default="", validation_alias="ONLINE_SALE_PUBLIC_BASE_URL"
    )
    online_sale_tailscale_base_url: str = Field(
        default="", validation_alias="ONLINE_SALE_TAILSCALE_BASE_URL"
    )
    online_sale_write_enabled: bool = Field(
        default=False, validation_alias="ONLINE_SALE_WRITE_ENABLED"
    )
    online_sale_token_secret: str = Field(
        default="", validation_alias="ONLINE_SALE_TOKEN_SECRET"
    )
    stock_check_token_secret: str = Field(
        default="", validation_alias="STOCK_CHECK_TOKEN_SECRET"
    )
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )

    @property
    def token_secret(self) -> str:
        return (self.online_sale_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def write_enabled(self) -> bool:
        return bool(self.online_sale_write_enabled)


@lru_cache
def get_online_sale_settings() -> OnlineSaleSettings:
    return OnlineSaleSettings()
