from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StockCheckSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    stock_check_enabled: bool = Field(default=False, validation_alias="STOCK_CHECK_ENABLED")
    stock_check_branch: str = Field(default="HQ", validation_alias="STOCK_CHECK_BRANCH")
    stock_check_token_secret: str = Field(
        default="",
        validation_alias="STOCK_CHECK_TOKEN_SECRET",
    )
    stock_check_token_ttl_seconds: int = Field(
        default=900,
        validation_alias="STOCK_CHECK_TOKEN_TTL_SECONDS",
    )
    # Idle window for unfinished leases; extended on count activity / heartbeat.
    stock_check_lease_idle_seconds: int = Field(
        default=300,
        validation_alias="STOCK_CHECK_LEASE_IDLE_SECONDS",
    )
    # Legacy alias — used only if STOCK_CHECK_LEASE_IDLE_SECONDS is unset in older envs.
    stock_check_lease_ttl_seconds: int = Field(
        default=300,
        validation_alias="STOCK_CHECK_LEASE_TTL_SECONDS",
    )
    stock_check_approver_line_user_ids: str = Field(
        default="",
        validation_alias="STOCK_CHECK_APPROVER_LINE_USER_IDS",
    )
    stock_check_data_dir: str = Field(
        default=".stock_check",
        validation_alias="STOCK_CHECK_DATA_DIR",
    )
    stock_check_listen_host: str = Field(
        default="0.0.0.0",
        validation_alias="STOCK_CHECK_LISTEN_HOST",
    )
    stock_check_listen_port: int = Field(
        default=8787,
        validation_alias="STOCK_CHECK_LISTEN_PORT",
    )
    # Reachable URL for LINE links; falls back to PUBLIC_BASE_URL then auto-detect.
    stock_check_public_base_url: str = Field(
        default="",
        validation_alias="STOCK_CHECK_PUBLIC_BASE_URL",
    )
    public_base_url: str = Field(default="", validation_alias="PUBLIC_BASE_URL")

    # Reuse companion MSSQL reader settings
    pos_mssql_server: str = Field(default="KSS", validation_alias="POS_MSSQL_SERVER")
    pos_mssql_database: str = Field(default="PARTS9", validation_alias="POS_MSSQL_DATABASE")
    pos_mssql_username: str = Field(default="python_reader", validation_alias="POS_MSSQL_USERNAME")
    pos_mssql_password: str = Field(default="", validation_alias="POS_MSSQL_PASSWORD")
    pos_mssql_driver: str = Field(
        default="ODBC Driver 17 for SQL Server",
        validation_alias="POS_MSSQL_DRIVER",
    )

    # Optional writer (separate login). Empty = attempt with reader (will fail until granted).
    pos_mssql_writer_username: str = Field(
        default="",
        validation_alias="POS_MSSQL_WRITER_USERNAME",
    )
    pos_mssql_writer_password: str = Field(
        default="",
        validation_alias="POS_MSSQL_WRITER_PASSWORD",
    )

    worker_name: str = Field(default="", validation_alias="WORKER_NAME")

    @field_validator("stock_check_branch")
    @classmethod
    def _branch(cls, value: str) -> str:
        branch = (value or "HQ").strip().upper()
        if branch not in {"HQ", "SYP"}:
            raise ValueError("STOCK_CHECK_BRANCH must be HQ or SYP")
        return branch

    @property
    def approver_ids(self) -> set[str]:
        raw = self.stock_check_approver_line_user_ids or ""
        return {part.strip() for part in raw.split(",") if part.strip()}

    @property
    def lease_idle_seconds(self) -> int:
        """Seconds without activity before unfinished leases return to the pool."""
        raw = self.stock_check_lease_idle_seconds or self.stock_check_lease_ttl_seconds or 300
        return max(60, int(raw))

    @property
    def bill_prefix(self) -> str:
        return "3SA" if self.stock_check_branch == "SYP" else "SA"

    @property
    def data_path(self) -> Path:
        path = Path(self.stock_check_data_dir)
        if not path.is_absolute():
            path = Path.cwd() / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sqlite_path(self) -> Path:
        return self.data_path / "stock_check.sqlite3"

    @property
    def resolved_public_base_url(self) -> str:
        from src.stock_check.net import resolve_stock_check_public_base_url

        detected = resolve_stock_check_public_base_url(
            explicit=self.stock_check_public_base_url,
            port=self.stock_check_listen_port,
        )
        if detected:
            return detected
        return f"http://127.0.0.1:{self.stock_check_listen_port}"


@lru_cache(maxsize=1)
def get_stock_check_settings() -> StockCheckSettings:
    return StockCheckSettings()


def clear_stock_check_settings_cache() -> None:
    get_stock_check_settings.cache_clear()
