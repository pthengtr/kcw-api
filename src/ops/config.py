from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kcw_ops_enabled: bool = Field(default=True, validation_alias="KCW_OPS_ENABLED")
    kcw_ops_site: str = Field(default="HQ", validation_alias="KCW_OPS_SITE")
    kcw_ops_listen_port: int = Field(default=8790, validation_alias="KCW_OPS_LISTEN_PORT")
    kcw_ops_public_base_url: str = Field(default="", validation_alias="KCW_OPS_PUBLIC_BASE_URL")
    kcw_ops_tailscale_base_url: str = Field(
        default="", validation_alias="KCW_OPS_TAILSCALE_BASE_URL"
    )
    kcw_ops_token_secret: str = Field(default="", validation_alias="KCW_OPS_TOKEN_SECRET")
    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )

    @property
    def token_secret(self) -> str:
        return (self.kcw_ops_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def site(self) -> str:
        return (self.kcw_ops_site or "HQ").strip().upper() or "HQ"


@lru_cache
def get_ops_settings() -> OpsSettings:
    return OpsSettings()
