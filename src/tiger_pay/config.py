from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PAYMENT_ID_EPOCH = "2026-09-01"

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
    tiger_pay_poll_webhook_quiet_seconds: float = Field(
        default=20.0,
        validation_alias="TIGER_PAY_POLL_WEBHOOK_QUIET_SECONDS",
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
    tiger_pay_id_epoch: str = Field(
        default=DEFAULT_PAYMENT_ID_EPOCH,
        validation_alias="TIGER_PAY_ID_EPOCH",
    )
    tiger_pay_sending_stale_seconds: float = Field(
        default=45.0,
        validation_alias="TIGER_PAY_SENDING_STALE_SECONDS",
    )
    tiger_pay_webhook_stale_hours: float = Field(
        default=24.0,
        validation_alias="TIGER_PAY_WEBHOOK_STALE_HOURS",
    )
    tiger_pay_eod_hour: int = Field(
        default=21,
        validation_alias="TIGER_PAY_EOD_HOUR",
    )
    tiger_pay_default_shop_code: str = Field(
        default="1",
        validation_alias="TIGER_PAY_DEFAULT_SHOP_CODE",
    )
    tiger_pay_change_denoms: tuple[int, ...] = Field(
        default=(100, 50, 20, 10, 5, 1),
        validation_alias="TIGER_PAY_CHANGE_DENOMS",
    )
    tiger_pay_change_warn_pieces: int = Field(
        default=10,
        validation_alias="TIGER_PAY_CHANGE_WARN_PIECES",
    )
    tiger_pay_change_crit_pieces: int = Field(
        default=2,
        validation_alias="TIGER_PAY_CHANGE_CRIT_PIECES",
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

    @field_validator("tiger_pay_default_shop_code")
    @classmethod
    def default_shop_code(cls, value: str) -> str:
        return (value or "1").strip() or "1"

    @field_validator("tiger_pay_change_denoms", mode="before")
    @classmethod
    def parse_change_denoms(cls, value: object) -> tuple[int, ...]:
        if isinstance(value, (list, tuple)):
            parts = value
        else:
            text = str(value or "").strip()
            if not text:
                return (100, 50, 20, 10, 5, 1)
            parts = [part.strip() for part in text.split(",") if part.strip()]
        denoms = tuple(int(part) for part in parts)
        if not denoms:
            raise ValueError("must include at least one denomination")
        if any(n <= 0 for n in denoms):
            raise ValueError("denominations must be positive")
        return denoms

    @field_validator("tiger_pay_eod_hour")
    @classmethod
    def eod_hour_range(cls, value: int) -> int:
        if value < 0 or value > 23:
            raise ValueError("must be between 0 and 23")
        return value

    @field_validator("tiger_pay_change_warn_pieces", "tiger_pay_change_crit_pieces")
    @classmethod
    def non_negative_pieces(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must not be negative")
        return value

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

    @field_validator("tiger_pay_id_epoch")
    @classmethod
    def payment_id_epoch(cls, value: str) -> str:
        stripped = value.strip() or DEFAULT_PAYMENT_ID_EPOCH
        parse_payment_id_epoch(stripped)
        return stripped

    @field_validator("tiger_pay_sending_stale_seconds", "tiger_pay_webhook_stale_hours")
    @classmethod
    def positive_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("tiger_pay_poll_webhook_quiet_seconds")
    @classmethod
    def non_negative_quiet_seconds(cls, value: float) -> float:
        if value < 0:
            raise ValueError("must not be negative")
        return value


def parse_payment_id_epoch(value: str) -> datetime:
    """Device payment ids were reset around Sep 2026; ignore older ids."""
    text = (value or "").strip() or DEFAULT_PAYMENT_ID_EPOCH
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("must be an ISO date or datetime") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@lru_cache
def get_tiger_pay_settings() -> TigerPaySettings:
    return TigerPaySettings()
