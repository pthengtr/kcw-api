from functools import lru_cache
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client, create_client

from src.tiger_pay.config import get_tiger_pay_settings

TIGER_PAY_SCHEMA = "tiger_pay"
INGEST_WEBHOOK_RPC = "ingest_webhook"


class TigerPayIngestError(Exception):
    def __init__(self, category: str, message: str | None = None) -> None:
        self.category = category
        self.message = message
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
        raise TigerPayIngestError("supabase_rpc_failed", str(exc.message or exc)) from exc

    return _parse_ingest_webhook_row(response.data)

