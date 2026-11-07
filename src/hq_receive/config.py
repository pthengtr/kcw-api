from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HqReceiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hq_receive_enabled: bool = Field(default=True, validation_alias="HQ_RECEIVE_ENABLED")
    hq_receive_listen_port: int = Field(
        default=8795, validation_alias="HQ_RECEIVE_LISTEN_PORT"
    )
    hq_receive_public_base_url: str = Field(
        default="", validation_alias="HQ_RECEIVE_PUBLIC_BASE_URL"
    )
    hq_receive_tailscale_base_url: str = Field(
        default="", validation_alias="HQ_RECEIVE_TAILSCALE_BASE_URL"
    )
    hq_receive_pimas_write_enabled: bool = Field(
        default=False, validation_alias="HQ_RECEIVE_PIMAS_WRITE_ENABLED"
    )
    hq_receive_cost_tolerance_pct: float = Field(
        default=2.0, validation_alias="HQ_RECEIVE_COST_TOLERANCE_PCT"
    )
    hq_receive_qty_tolerance: float = Field(
        default=0.0001, validation_alias="HQ_RECEIVE_QTY_TOLERANCE"
    )
    hq_receive_total_tolerance: float = Field(
        default=1.0, validation_alias="HQ_RECEIVE_TOTAL_TOLERANCE"
    )
    hq_receive_ai_model: str = Field(
        default="", validation_alias="HQ_RECEIVE_AI_MODEL"
    )
    hq_receive_sticker_printer_model: str = Field(
        default="te310", validation_alias="HQ_RECEIVE_STICKER_PRINTER_MODEL"
    )
    hq_receive_sticker_printer_host: str = Field(
        default="", validation_alias="HQ_RECEIVE_STICKER_PRINTER_HOST"
    )
    hq_receive_token_secret: str = Field(
        default="", validation_alias="HQ_RECEIVE_TOKEN_SECRET"
    )
    stock_check_token_secret: str = Field(
        default="", validation_alias="STOCK_CHECK_TOKEN_SECRET"
    )
    stock_check_token_ttl_seconds: int = Field(
        default=86400, validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS"
    )
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(
        default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    @property
    def token_secret(self) -> str:
        return (self.hq_receive_token_secret or self.stock_check_token_secret or "").strip()

    @property
    def write_enabled(self) -> bool:
        return bool(self.hq_receive_pimas_write_enabled)


@lru_cache
def get_hq_receive_settings() -> HqReceiveSettings:
    return HqReceiveSettings()
