import hashlib
import json
import logging
import time
import uuid
from typing import Any

from fastapi import BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.db import get_engine
from src.tiger_pay.auth import TigerPayAuthError, verify_webhook_authorization
from src.tiger_pay.client import ingest_webhook_sync
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.digest import compute_body_sha256
from src.tiger_pay.models import TigerPayIngestResult, TigerPayWebhookPayload
from src.tiger_pay.normalize import (
    blank_to_none,
    decimal_to_json_string,
    normalize_change_amount,
    normalize_positive_decimal,
    normalize_tiger_timestamp,
)
from src.tiger_pay.payload import sanitize_webhook_payload
from src.tiger_pay.payment_service import reconcile_from_webhook_transaction

logger = logging.getLogger("kcw.tiger_pay")

_INGEST_ATTEMPTS = 3
_INGEST_RETRY_DELAYS = (0.25, 0.5)


class TigerPayWebhookError(Exception):
    def __init__(self, status_code: int, error: str, error_category: str | None = None) -> None:
        self.status_code = status_code
        self.error = error
        self.error_category = error_category
        super().__init__(error)


def _request_id(request: Request) -> str:
    header_value = request.headers.get("x-request-id", "").strip()
    return header_value or str(uuid.uuid4())


def _error_response(status_code: int, error: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"ok": False, "error": error})


def _success_response(duplicate: bool, transaction_updated: bool) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "duplicate": duplicate,
            "transaction_updated": transaction_updated,
        },
    )


def build_event_key(payment_id: int, payment_status: str, payment_updated_at: str, body_sha256: str) -> str:
    stable_input = (
        f"{payment_id}|{payment_status}|{payment_updated_at}|{body_sha256}"
    )
    return hashlib.sha256(stable_input.encode("utf-8")).hexdigest()


def build_transaction(payload: TigerPayWebhookPayload) -> dict[str, str | int | None]:
    payment = payload.payment
    shop = payload.shop

    amount = normalize_positive_decimal(payment.amount, "payment.amount")
    total_pay = normalize_positive_decimal(payment.totalPay, "payment.totalPay")
    change_amount = normalize_change_amount(payment.change)

    return {
        "tiger_payment_id": payment.id,
        "payment_no": payment.paymentNo,
        "payment_type": payment.type.strip().lower(),
        "status": payment.status.strip().lower(),
        "amount": decimal_to_json_string(amount),
        "total_pay": decimal_to_json_string(total_pay),
        "change_amount": decimal_to_json_string(change_amount),
        "ref_no_1": blank_to_none(payment.refNo1),
        "ref_no_2": blank_to_none(payment.refNo2),
        "note": blank_to_none(payment.note),
        "remark": blank_to_none(payment.remark),
        "shop_code": blank_to_none(shop.name),
        "shop_name": blank_to_none(shop.shopName),
        "branch_name": blank_to_none(shop.branchName),
        "tiger_created_at": normalize_tiger_timestamp(payment.createdAt),
        "tiger_updated_at": normalize_tiger_timestamp(payment.updatedAt),
    }


def persist_accepted_webhook(
    *,
    request_id: str,
    event_key: str,
    body_sha256: str,
    transaction: dict[str, str | int | None],
    sanitized_payload: dict[str, Any],
    started_at: float,
) -> None:
    """Supabase ingest + companion reconcile after the cashbox already got 200."""
    ingest_result = None
    last_error: BaseException | None = None
    for attempt in range(1, _INGEST_ATTEMPTS + 1):
        try:
            ingest_result = ingest_webhook_sync(
                event_key,
                body_sha256,
                transaction,
                sanitized_payload,
            )
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            logger.warning(
                "tiger_pay webhook ingest attempt failed request_id=%s "
                "tiger_payment_id=%s attempt=%s/%s",
                request_id,
                transaction.get("tiger_payment_id"),
                attempt,
                _INGEST_ATTEMPTS,
                exc_info=True,
            )
            if attempt < _INGEST_ATTEMPTS:
                time.sleep(_INGEST_RETRY_DELAYS[min(attempt - 1, len(_INGEST_RETRY_DELAYS) - 1)])

    duplicate = False
    transaction_updated = False
    if ingest_result is not None:
        try:
            parsed = TigerPayIngestResult.model_validate(ingest_result)
            duplicate = parsed.duplicate
            transaction_updated = parsed.transaction_updated
        except ValidationError:
            logger.error(
                "tiger_pay webhook ingest result invalid request_id=%s tiger_payment_id=%s",
                request_id,
                transaction.get("tiger_payment_id"),
            )
    elif last_error is not None:
        logger.error(
            "tiger_pay webhook ingest failed after retries request_id=%s "
            "tiger_payment_id=%s error_category=%s",
            request_id,
            transaction.get("tiger_payment_id"),
            getattr(last_error, "category", type(last_error).__name__),
        )

    try:
        reconcile_from_webhook_transaction(
            get_engine(),
            transaction,
            event_key=f"webhook:{event_key}",
        )
    except Exception:
        logger.exception(
            "tiger_pay webhook attempt reconcile failed request_id=%s tiger_payment_id=%s",
            request_id,
            transaction.get("tiger_payment_id"),
        )

    logger.info(
        "tiger_pay webhook persisted request_id=%s tiger_payment_id=%s payment_no=%s "
        "payment_type=%s payment_status=%s duplicate=%s transaction_updated=%s "
        "ingest_ok=%s duration_ms=%.1f",
        request_id,
        transaction.get("tiger_payment_id"),
        transaction.get("payment_no"),
        transaction.get("payment_type"),
        transaction.get("status"),
        duplicate,
        transaction_updated,
        ingest_result is not None,
        (time.perf_counter() - started_at) * 1000,
    )


def parse_webhook_payload(raw_body: bytes) -> tuple[dict[str, Any], TigerPayWebhookPayload]:
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise TigerPayWebhookError(400, "Invalid webhook payload", "payload_invalid_json") from exc

    if not isinstance(parsed, dict):
        raise TigerPayWebhookError(400, "Invalid webhook payload", "payload_invalid_shape")

    try:
        validated = TigerPayWebhookPayload.model_validate(parsed)
    except ValidationError as exc:
        raise TigerPayWebhookError(400, "Invalid webhook payload", "payload_validation_failed") from exc

    return parsed, validated


async def process_tiger_pay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    started_at = time.perf_counter()
    request_id = _request_id(request)
    settings = get_tiger_pay_settings()

    try:
        raw_body = await request.body()
        if not raw_body:
            raise TigerPayWebhookError(400, "Invalid webhook payload", "payload_empty")

        if len(raw_body) > settings.tiger_pay_max_body_bytes:
            raise TigerPayWebhookError(413, "Webhook payload too large", "payload_too_large")

        try:
            verify_webhook_authorization(
                request.headers.get("Authorization"),
                raw_body,
                settings.tiger_pay_client_secret,
            )
        except TigerPayAuthError as exc:
            logger.warning(
                "tiger_pay webhook unauthorized request_id=%s error_category=%s duration_ms=%.1f",
                request_id,
                exc.reason_code,
                (time.perf_counter() - started_at) * 1000,
            )
            return _error_response(401, "Unauthorized")

        body_sha256 = compute_body_sha256(raw_body)
        parsed_payload, validated_payload = parse_webhook_payload(raw_body)
        transaction = build_transaction(validated_payload)
        sanitized_payload = sanitize_webhook_payload(parsed_payload)

        payment = validated_payload.payment
        event_key = build_event_key(
            payment.id,
            payment.status,
            payment.updatedAt,
            body_sha256,
        )

        background_tasks.add_task(
            persist_accepted_webhook,
            request_id=request_id,
            event_key=event_key,
            body_sha256=body_sha256,
            transaction=transaction,
            sanitized_payload=sanitized_payload,
            started_at=started_at,
        )
        logger.info(
            "tiger_pay webhook accepted request_id=%s tiger_payment_id=%s payment_no=%s "
            "payment_type=%s payment_status=%s duration_ms=%.1f",
            request_id,
            payment.id,
            payment.paymentNo,
            transaction["payment_type"],
            transaction["status"],
            (time.perf_counter() - started_at) * 1000,
        )
        # ACK before Supabase. Body flags are placeholders; persist logs the real ones.
        return _success_response(duplicate=False, transaction_updated=True)

    except TigerPayWebhookError as exc:
        logger.warning(
            "tiger_pay webhook rejected request_id=%s error_category=%s duration_ms=%.1f",
            request_id,
            exc.error_category or "webhook_rejected",
            (time.perf_counter() - started_at) * 1000,
        )
        return _error_response(exc.status_code, exc.error)

    except Exception:
        logger.exception(
            "tiger_pay webhook failed request_id=%s error_category=internal_error duration_ms=%.1f",
            request_id,
            (time.perf_counter() - started_at) * 1000,
        )
        return _error_response(500, "Webhook processing failed")
