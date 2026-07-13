from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_BODY_BYTES = 5 * 1024 * 1024


class TigerPaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tiger_pay_client_secret: str = Field(validation_alias="TIGER_PAY_CLIENT_SECRET")
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    tiger_pay_max_body_bytes: int = Field(
        default=DEFAULT_MAX_BODY_BYTES,
        validation_alias="TIGER_PAY_MAX_BODY_BYTES",
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

    @field_validator("tiger_pay_max_body_bytes")
    @classmethod
    def positive_max_body_bytes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value


@lru_cache
def get_tiger_pay_settings() -> TigerPaySettings:
    return TigerPaySettings()
