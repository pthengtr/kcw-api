#!/usr/bin/env python3
"""Test tiger_pay.ingest_webhook connectivity against Supabase."""

from __future__ import annotations

import json
import sys

from postgrest.exceptions import APIError

from src.tiger_pay.client import (
    TIGER_PAY_SCHEMA,
    INGEST_WEBHOOK_RPC,
    get_tiger_pay_supabase_client,
    ingest_webhook_sync,
    normalize_ingest_result_row,
)
from src.tiger_pay.config import get_tiger_pay_settings


def _print_settings_summary() -> None:
    settings = get_tiger_pay_settings()
    print(f"SUPABASE_URL={settings.supabase_url}")
    print(f"schema={TIGER_PAY_SCHEMA} rpc={INGEST_WEBHOOK_RPC}")
    print(f"max_body_bytes={settings.tiger_pay_max_body_bytes}")


def _probe_schema_access() -> None:
    client = get_tiger_pay_supabase_client()
    try:
        client.schema(TIGER_PAY_SCHEMA).rpc(
            INGEST_WEBHOOK_RPC,
            {
                "p_event_key": "diagnostic-probe",
                "p_body_sha256": "0" * 64,
                "p_transaction": {
                    "tiger_payment_id": 0,
                    "payment_no": "DIAG",
                    "payment_type": "cash",
                    "status": "success",
                    "amount": "0",
                    "total_pay": "0",
                    "change_amount": "0",
                    "ref_no_1": None,
                    "ref_no_2": None,
                    "note": None,
                    "remark": None,
                    "shop_code": "DIAG",
                    "shop_name": "Diagnostic",
                    "branch_name": "Diagnostic",
                    "tiger_created_at": "2026-07-13T14:00:00+07:00",
                    "tiger_updated_at": "2026-07-13T14:00:10+07:00",
                },
                "p_payload": {"diagnostic": True},
            },
        ).execute()
        print("rpc_call=ok")
    except APIError as exc:
        print("rpc_call=failed")
        print(f"supabase_code={exc.code or '-'}")
        print(f"message={exc.message or exc}")
        if exc.hint:
            print(f"hint={exc.hint}")
        if exc.details:
            print(f"details={exc.details}")
        raise SystemExit(1) from exc


def main() -> int:
    _print_settings_summary()

    sample_payload = {
        "payment": {
            "id": 1415,
            "type": "cash",
            "paymentNo": "PA_TEST_0001",
            "amount": 100,
            "totalPay": 100,
            "refNo1": "TEST-REF-001",
            "refNo2": None,
            "note": "Postman test",
            "status": "success",
            "remark": None,
            "createdAt": "2026-07-13T14:00:00+07:00",
            "updatedAt": "2026-07-13T14:00:10+07:00",
            "cashList": [],
            "category": None,
            "tag": {"id": 2, "name": "Cashier"},
            "change": {
                "transactionNo": None,
                "amount": 0,
                "dispensed": 0,
                "cashList": [],
            },
            "dynamicQR": None,
            "promptPay": None,
            "drop": None,
        },
        "shop": {
            "name": "TEST-MACHINE-01",
            "shopName": "KCW Test Shop",
            "branchName": "Head Office",
        },
    }

    from src.tiger_pay.digest import compute_body_sha256
    from src.tiger_pay.models import TigerPayWebhookPayload
    from src.tiger_pay.payload import sanitize_webhook_payload
    from src.tiger_pay.service import build_event_key, build_transaction

    raw = json.dumps(sample_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    validated = TigerPayWebhookPayload.model_validate(sample_payload)
    transaction = build_transaction(validated)
    sanitized = sanitize_webhook_payload(sample_payload)
    body_sha256 = compute_body_sha256(raw)
    event_key = build_event_key(
        validated.payment.id,
        validated.payment.status,
        validated.payment.updatedAt,
        body_sha256,
    )

    print("event_key=", event_key)
    print("transaction=", json.dumps(transaction, ensure_ascii=False))

    try:
        result = ingest_webhook_sync(event_key, body_sha256, transaction, sanitized)
    except Exception as exc:
        print(f"ingest_failed={type(exc).__name__}: {exc}")
        return 1

    print("ingest_result=", json.dumps(result, ensure_ascii=False))
    print("normalized=", json.dumps(normalize_ingest_result_row(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
