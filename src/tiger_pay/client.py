from functools import lru_cache

from supabase import Client, create_client

from src.tiger_pay.config import get_tiger_pay_settings

TIGER_PAY_SCHEMA = "tiger_pay"
INGEST_WEBHOOK_RPC = "ingest_webhook"


@lru_cache
def get_tiger_pay_supabase_client() -> Client:
    settings = get_tiger_pay_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def ingest_webhook_sync(
    event_key: str,
    body_sha256: str,
    transaction: dict[str, object],
    payload: dict[str, object],
) -> dict[str, object]:
    client = get_tiger_pay_supabase_client()
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

    rows = response.data
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RuntimeError("unexpected ingest_webhook response shape")

    return rows[0]
