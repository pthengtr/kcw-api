from functools import lru_cache
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client, create_client

from src.tiger_pay.config import get_tiger_pay_settings

TIGER_PAY_SCHEMA = "tiger_pay"
INGEST_WEBHOOK_RPC = "ingest_webhook"


class TigerPayIngestError(Exception):
    def __init__(
        self,
        category: str,
        message: str | None = None,
        *,
        supabase_code: str | None = None,
    ) -> None:
        self.category = category
        self.message = message
        self.supabase_code = supabase_code
        super().__init__(category)


@lru_cache
def get_tiger_pay_supabase_client() -> Client:
    settings = get_tiger_pay_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _parse_ingest_webhook_row(data: Any) -> dict[str, object]:
    if isinstance(data, list):
        if len(data) != 1 or not isinstance(data[0], dict):
            raise TigerPayIngestError("rpc_response_shape_invalid")
        return data[0]

    if isinstance(data, dict):
        return data

    raise TigerPayIngestError("rpc_response_shape_invalid")


def normalize_ingest_result_row(row: dict[str, object]) -> dict[str, object]:
    def pick(*keys: str) -> object:
        for key in keys:
            if key in row:
                return row[key]
        return None

    event_id = pick("event_id", "eventId")
    duplicate = pick("duplicate", "is_duplicate", "isDuplicate")
    transaction_updated = pick(
        "transaction_updated",
        "transactionUpdated",
        "is_transaction_updated",
    )

    if event_id is None or duplicate is None or transaction_updated is None:
        raise TigerPayIngestError("rpc_response_fields_missing")

    return {
        "event_id": event_id,
        "duplicate": _coerce_bool(duplicate),
        "transaction_updated": _coerce_bool(transaction_updated),
    }


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "t", "1", "yes"}:
            return True
        if lowered in {"false", "f", "0", "no"}:
            return False
    if isinstance(value, int):
        return bool(value)
    raise TigerPayIngestError("rpc_response_fields_invalid")


def ingest_webhook_sync(
    event_key: str,
    body_sha256: str,
    transaction: dict[str, object],
    payload: dict[str, object],
) -> dict[str, object]:
    client = get_tiger_pay_supabase_client()
    try:
        response = (
            client.schema(TIGER_PAY_SCHEMA)
            .rpc(
                INGEST_WEBHOOK_RPC,
                {
                    "p_event_key": event_key,
                    "p_body_sha256": body_sha256,
                    "p_transaction": transaction,
                    "p_payload": payload,
                },
            )
            .execute()
        )
    except APIError as exc:
        raise TigerPayIngestError(
            "supabase_rpc_failed",
            str(exc.message or exc),
            supabase_code=exc.code,
        ) from exc

    row = _parse_ingest_webhook_row(response.data)
    return normalize_ingest_result_row(row)

