from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_BODY_BYTES = 5 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class TigerPaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absolute path so uvicorn --reload / different CWDs still find .env
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        # Empty Windows env vars must not override values from .env
        env_ignore_empty=True,
        extra="ignore",
    )

    tiger_pay_client_secret: str = Field(validation_alias="TIGER_PAY_CLIENT_SECRET")
    tiger_pay_client_id: str = Field(
        default="",
        validation_alias="TIGER_PAY_CLIENT_ID",
    )
    tiger_pay_api_host: str = Field(
        default="",
        validation_alias="TIGER_PAY_API_HOST",
    )
    tiger_pay_poll_interval_seconds: float = Field(
        default=1.5,
        validation_alias="TIGER_PAY_POLL_INTERVAL_SECONDS",
    )
    tiger_pay_qr_gateway: str = Field(
        default="KBANK",
        validation_alias="TIGER_PAY_QR_GATEWAY",
    )
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    tiger_pay_max_body_bytes: int = Field(
        default=DEFAULT_MAX_BODY_BYTES,
        validation_alias="TIGER_PAY_MAX_BODY_BYTES",
    )
    tiger_voucher_api_host: str = Field(
        default="https://api.tigercashbox.com",
        validation_alias="TIGER_VOUCHER_API_HOST",
    )
    tiger_voucher_username: str = Field(
        default="",
        validation_alias="TIGER_VOUCHER_USERNAME",
    )
    tiger_voucher_password: str = Field(
        default="",
        validation_alias="TIGER_VOUCHER_PASSWORD",
    )
    tiger_voucher_mobile: str = Field(
        default="",
        validation_alias="TIGER_VOUCHER_MOBILE",
    )
    tiger_voucher_authen_required: str = Field(
        default="0",
        validation_alias="TIGER_VOUCHER_AUTHEN_REQUIRED",
    )
    tiger_voucher_approved_required: str = Field(
        default="0",
        validation_alias="TIGER_VOUCHER_APPROVED_REQUIRED",
    )
    tiger_voucher_expire_hours: float = Field(
        default=8.0,
        validation_alias="TIGER_VOUCHER_EXPIRE_HOURS",
    )

    @field_validator(
        "tiger_pay_client_secret",
        "supabase_url",
        "supabase_service_role_key",
    )
    @classmethod
    def required_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator(
        "tiger_pay_client_id",
        "tiger_pay_api_host",
        "tiger_voucher_api_host",
        "tiger_voucher_username",
        "tiger_voucher_password",
        "tiger_voucher_mobile",
        "tiger_voucher_authen_required",
        "tiger_voucher_approved_required",
    )
    @classmethod
    def strip_optional(cls, value: str) -> str:
        return value.strip()

    @field_validator("tiger_voucher_expire_hours")
    @classmethod
    def positive_voucher_expire_hours(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("tiger_pay_qr_gateway")
    @classmethod
    def qr_gateway(cls, value: str) -> str:
        cleaned = value.strip().upper() or "KBANK"
        if cleaned not in {"KBANK", "SCB"}:
            raise ValueError("must be KBANK or SCB")
        return cleaned

    @field_validator("tiger_pay_poll_interval_seconds")
    @classmethod
    def positive_poll_interval(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("tiger_pay_max_body_bytes")
    @classmethod
    def positive_max_body_bytes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value


@lru_cache
def get_tiger_pay_settings() -> TigerPaySettings:
    return TigerPaySettings()
