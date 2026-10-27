from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ToBillSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    to_bill_enabled: bool = Field(default=True, validation_alias="TO_BILL_ENABLED")
    to_bill_listen_port: int = Field(default=8794, validation_alias="TO_BILL_LISTEN_PORT")
    to_bill_public_base_url: str = Field(default="", validation_alias="TO_BILL_PUBLIC_BASE_URL")
    to_bill_tailscale_base_url: str = Field(
        default="", validation_alias="TO_BILL_TAILSCALE_BASE_URL"
    )
    to_bill_token_secret: str = Field(default="", validation_alias="TO_BILL_TOKEN_SECRET")
    to_bill_seller_tax_id: str = Field(default="", validation_alias="TO_BILL_SELLER_TAX_ID")
    stock_check_token_secret: str = Field(default="", validation_alias="STOCK_CHECK_TOKEN_SECRET")
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )

    @property
    def token_secret(self) -> str:
        return (self.to_bill_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def seller_tax_id(self) -> str:
        digits = "".join(ch for ch in (self.to_bill_seller_tax_id or "") if ch.isdigit())
        return digits


@lru_cache
def get_to_bill_settings() -> ToBillSettings:
    return ToBillSettings()
