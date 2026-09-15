from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from src.companion.bills import get_open_bill, list_open_bills
from src.tiger_pay import repos
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError, get_open_api_client
from src.tiger_pay.payload import omit_qr_images
from src.tiger_pay.qr import (
    companion_qr_from_attempt,
    extract_companion_qr,
    has_displayable_qr,
    merge_qr_payload_into_payment,
    payment_type_from_attempt,
    should_confirm_qr_payment,
)
from src.tiger_pay.status import is_active_status, normalize_status

logger = logging.getLogger("kcw.tiger_pay.payment_service")

# Tiger Open API: RefNo2 max length is 20.
TIGER_REF_NO2_MAX_LEN = 20
ALLOWED_PAYMENT_TYPES = frozenset({"cash", "qr"})


def new_payment_attempt_id() -> str:
    """Generate an internal attempt id that fits Tiger RefNo2 (<=20)."""
    return uuid.uuid4().hex[:TIGER_REF_NO2_MAX_LEN]


class PaymentServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "payment_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


def list_bills_with_payment_status(
    engine: Engine,
    *,
    mode: str | None = None,
    limit: int | str | None = None,
) -> list[dict[str, Any]]:
    bills = list_open_bills(mode=mode, limit=limit)
    latest_by_bill = repos.list_latest_attempts_by_bill_ids(
        engine,
        [bill.id for bill in bills],
    )
    results: list[dict[str, Any]] = []
    for bill in bills:
        attempt = latest_by_bill.get(bill.id)
        item = bill.to_dict()
        item["tiger_payment_status"] = attempt["status"] if attempt else None
        item["tiger_payment_no"] = attempt["tiger_payment_no"] if attempt else None
        item["tiger_payment_id"] = attempt["tiger_payment_id"] if attempt else None
        item["payment_attempt_id"] = attempt["id"] if attempt else None
        item["payment_attempt_active"] = bool(
            attempt and is_active_status(str(attempt["status"]))
        )
        item["payment_type"] = payment_type_from_attempt(attempt) if attempt else None
        results.append(item)
    return results


def get_attempt_detail(engine: Engine, attempt_id: str) -> dict[str, Any]:
    attempt = repos.get_payment_attempt(engine, attempt_id)
    if not attempt:
        raise PaymentServiceError("Payment attempt not found", code="not_found")
    events = repos.list_payment_events(engine, attempt_id)
    qr = companion_qr_from_attempt(attempt)
    attempt_out = dict(attempt)
    if attempt_out.get("raw_create_response") is not None:
        attempt_out["raw_create_response"] = omit_qr_images(attempt_out["raw_create_response"])
    return {
        "attempt": attempt_out,
        "events": events,
        "qr": qr,
        "payment_type": payment_type_from_attempt(attempt),
    }


def send_payment_for_bill(
    engine: Engine,
    pos_bill_id: str,
    *,
    payment_type: str = "cash",
    open_api: TigerPayOpenApiClient | None = None,
) -> dict[str, Any]:
    cleaned_type = str(payment_type or "cash").strip().lower()
    if cleaned_type not in ALLOWED_PAYMENT_TYPES:
        raise PaymentServiceError(
            "payment_type must be cash or qr",
            code="invalid_payment_type",
        )

    bill = get_open_bill(pos_bill_id)
    if bill is None:
        raise PaymentServiceError("POS bill not found", code="bill_not_found")

    existing = repos.get_active_attempt_for_bill(engine, pos_bill_id)
    if existing:
        raise PaymentServiceError(
            "Bill already has an active payment attempt",
            code="active_attempt_exists",
        )

    client = open_api or get_open_api_client()
    try:
        current = client.get_current()
    except TigerPayOpenApiError as exc:
        raise PaymentServiceError(
            f"Unable to check Tiger current payment: {exc.message}",
            code="tiger_current_failed",
        ) from exc

    if current is not None:
        raise PaymentServiceError(
            "Tiger Pay already has an active payment",
            code="tiger_busy",
        )

    attempt_id = new_payment_attempt_id()
    try:
        attempt = repos.create_payment_attempt(
            engine,
            attempt_id=attempt_id,
            pos_bill_id=bill.id,
            pos_bill_number=bill.bill_number,
            amount=bill.amount,
            status="sending",
            raw_status="sending",
        )
    except IntegrityError as exc:
        raise PaymentServiceError(
            "Bill already has an active payment attempt",
            code="active_attempt_exists",
        ) from exc

    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status="sending",
        payload={"action": "payment_created", "pos_bill_id": bill.id},
        event_key=f"api:created:{attempt_id}",
    )

    note = f"POS bill {bill.bill_number}"
    amount_value: float | int = float(bill.amount)
    if float(amount_value).is_integer():
        amount_value = int(amount_value)
    try:
        create_kwargs: dict = {
            "amount": amount_value,
            "ref_no_1": bill.bill_number,
            "ref_no_2": str(attempt_id),
            "note": note,
            "payment_type": cleaned_type,
        }
        if cleaned_type == "qr":
            create_kwargs["payment_gateway"] = get_tiger_pay_settings().tiger_pay_qr_gateway
        create_result = client.create_payment(**create_kwargs)
        create_result = _ensure_qr_on_create(
            client,
            create_result,
            payment_type=cleaned_type,
        )
    except TigerPayOpenApiError as exc:
        repos.update_payment_attempt(
            engine,
            attempt_id,
            status="failed",
            raw_status="failed",
            error_message=exc.message,
            raw_create_response={
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=attempt_id,
            source="api",
            status="failed",
            payload={
                "action": "create_failed",
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
            event_key=f"api:create_failed:{attempt_id}",
        )
        raise PaymentServiceError(
            f"Tiger create payment failed: {exc.message}",
            code="tiger_create_failed",
            details={"status_code": exc.status_code, "tiger": exc.payload},
        ) from exc

    data = create_result.get("data") or {}
    raw_status = str(data.get("status") or "pending")
    status = normalize_status(raw_status)
    tiger_payment_id = data.get("id")
    tiger_payment_no = data.get("paymentNo")

    updated = repos.update_payment_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        tiger_payment_id=int(tiger_payment_id) if tiger_payment_id is not None else None,
        tiger_payment_no=str(tiger_payment_no) if tiger_payment_no is not None else None,
        raw_create_response=create_result.get("raw") or create_result,
        clear_error=True,
    )
    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status=status,
        payload={
            "action": "api_response_received",
            "create_response": omit_qr_images(create_result.get("raw") or create_result),
            "payment_type": cleaned_type,
        },
        event_key=f"api:create_response:{attempt_id}:{raw_status}",
    )

    attempt_out = dict(updated or attempt)
    if attempt_out.get("raw_create_response") is not None:
        attempt_out["raw_create_response"] = omit_qr_images(attempt_out["raw_create_response"])
    return {
        "attempt": attempt_out,
        "create_response": omit_qr_images(create_result),
        "qr": extract_companion_qr(create_result.get("raw") or create_result),
        "payment_type": cleaned_type,
    }


def cancel_payment_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    open_api: TigerPayOpenApiClient | None = None,
) -> dict[str, Any]:
    attempt = repos.get_payment_attempt(engine, attempt_id)
    if not attempt:
        raise PaymentServiceError("Payment attempt not found", code="not_found")

    if not is_active_status(str(attempt["status"])):
        raise PaymentServiceError(
            "Payment attempt is not active",
            code="not_active",
        )

    tiger_payment_id = attempt.get("tiger_payment_id")
    if tiger_payment_id is None:
        raise PaymentServiceError(
            "Tiger payment id is missing; cannot cancel yet",
            code="missing_tiger_id",
        )

    updated = repos.update_payment_attempt(
        engine,
        attempt_id,
        status="cancelling",
        raw_status="cancelling",
    )
    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status="cancelling",
        payload={"action": "cancellation_requested"},
        event_key=f"api:cancel_requested:{attempt_id}",
    )

    client = open_api or get_open_api_client()
    try:
        cancel_result = client.cancel_payment(tiger_payment_id)
    except TigerPayOpenApiError as exc:
        repos.update_payment_attempt(
            engine,
            attempt_id,
            error_message=exc.message,
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=attempt_id,
            source="api",
            status="cancelling",
            payload={
                "action": "cancel_api_failed",
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
            event_key=f"api:cancel_failed:{attempt_id}:{exc.status_code}",
        )
        raise PaymentServiceError(
            f"Tiger cancel failed: {exc.message}",
            code="tiger_cancel_failed",
        ) from exc

    # Keep local status as cancelling until webhook or polling confirms.
    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status="cancelling",
        payload={
            "action": "cancel_api_response",
            "cancel_response": cancel_result.get("raw") or cancel_result,
        },
        event_key=f"api:cancel_response:{attempt_id}",
    )
    repos.update_payment_attempt(
        engine,
        attempt_id,
        status="cancelling",
        raw_status="cancelling",
        clear_error=True,
    )

    return {
        "attempt": repos.get_payment_attempt(engine, attempt_id) or updated or attempt,
        "cancel_response": cancel_result,
        "events": repos.list_payment_events(engine, attempt_id),
    }


def apply_status_update(
    engine: Engine,
    *,
    attempt_id: str,
    raw_status: str,
    source: str,
    payload: dict[str, Any] | None = None,
    event_key: str | None = None,
    tiger_payment_id: int | None = None,
    tiger_payment_no: str | None = None,
    touch_last_polled: bool = False,
) -> dict[str, Any] | None:
    status = normalize_status(raw_status)
    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source=source,
        status=status,
        payload=payload or {"raw_status": raw_status},
        event_key=event_key,
    )
    # Duplicate event_key: still refresh status from source of truth.
    return repos.update_payment_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        tiger_payment_id=tiger_payment_id,
        tiger_payment_no=tiger_payment_no,
        touch_last_polled=touch_last_polled,
        clear_error=True,
    )


def reconcile_from_tiger_payment(
    engine: Engine,
    payment: dict[str, Any],
    *,
    source: str,
    event_key: str | None = None,
    touch_last_polled: bool = False,
) -> dict[str, Any] | None:
    tiger_payment_id_raw = payment.get("id") or payment.get("tiger_payment_id")
    tiger_payment_id: int | None
    try:
        tiger_payment_id = int(tiger_payment_id_raw) if tiger_payment_id_raw is not None else None
    except (TypeError, ValueError):
        tiger_payment_id = None

    ref_no_2 = payment.get("refNo2") or payment.get("ref_no_2")
    if ref_no_2 is not None:
        ref_no_2 = str(ref_no_2).strip() or None

    attempt = repos.find_attempt_by_tiger_or_ref(
        engine,
        tiger_payment_id=tiger_payment_id,
        ref_no_2=ref_no_2,
    )
    if not attempt:
        logger.info(
            "No payment attempt matched tiger_payment_id=%s ref_no_2=%s source=%s",
            tiger_payment_id,
            ref_no_2,
            source,
        )
        return None

    raw_status = str(payment.get("status") or payment.get("raw_status") or "unknown")
    payment_no = payment.get("paymentNo") or payment.get("payment_no") or attempt.get(
        "tiger_payment_no"
    )
    key = event_key or f"{source}:{attempt['id']}:{tiger_payment_id}:{raw_status}"
    return apply_status_update(
        engine,
        attempt_id=str(attempt["id"]),
        raw_status=raw_status,
        source=source,
        payload={"action": f"{source}_update", "payment": omit_qr_images(payment)},
        event_key=key,
        tiger_payment_id=tiger_payment_id,
        tiger_payment_no=str(payment_no) if payment_no is not None else None,
        touch_last_polled=touch_last_polled,
    )


def reconcile_from_webhook_transaction(
    engine: Engine,
    transaction: dict[str, Any],
    *,
    event_key: str | None = None,
) -> dict[str, Any] | None:
    payment = {
        "id": transaction.get("tiger_payment_id"),
        "tiger_payment_id": transaction.get("tiger_payment_id"),
        "paymentNo": transaction.get("payment_no"),
        "status": transaction.get("status"),
        "refNo2": transaction.get("ref_no_2"),
        "ref_no_2": transaction.get("ref_no_2"),
    }
    return reconcile_from_tiger_payment(
        engine,
        payment,
        source="webhook",
        event_key=event_key,
    )


def _ensure_qr_on_create(
    client: TigerPayOpenApiClient,
    create_result: dict[str, Any],
    *,
    payment_type: str,
) -> dict[str, Any]:
    if payment_type != "qr":
        return create_result
    data = create_result.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    if has_displayable_qr(data) or has_displayable_qr(create_result.get("raw") or create_result):
        return create_result

    tiger_payment_id = data.get("id")
    if tiger_payment_id is None:
        return create_result

    settings = get_tiger_pay_settings()
    try:
        qr_result = client.create_qr(
            tiger_payment_id,
            payment_gateway=settings.tiger_pay_qr_gateway,
        )
    except TigerPayOpenApiError as exc:
        logger.warning(
            "QR create fallback failed tiger_payment_id=%s error=%s",
            tiger_payment_id,
            exc.message,
        )
        return create_result
    merged = merge_qr_payload_into_payment(data, qr_result)
    updated = dict(create_result)
    updated["data"] = merged
    raw = create_result.get("raw")
    if isinstance(raw, dict):
        updated_raw = dict(raw)
        updated_raw["data"] = merged
        updated["raw"] = updated_raw
    else:
        updated["raw"] = {"data": merged, "message": qr_result.get("message")}
    return updated


def _confirm_qr_if_paid(
    engine: Engine,
    *,
    attempt: dict[str, Any],
    payment: dict[str, Any],
    client: TigerPayOpenApiClient,
) -> dict[str, Any]:
    if not should_confirm_qr_payment(payment):
        return payment

    tiger_payment_id = attempt.get("tiger_payment_id") or payment.get("id")
    if tiger_payment_id is None:
        return payment

    attempt_id = str(attempt["id"])
    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status=str(attempt.get("status") or "pending"),
        payload={"action": "confirm_requested", "tiger_payment_id": tiger_payment_id},
        event_key=f"api:confirm_requested:{attempt_id}",
    )
    try:
        confirm_result = client.confirm_payment(tiger_payment_id)
    except TigerPayOpenApiError as exc:
        logger.warning(
            "QR confirm failed attempt_id=%s tiger_payment_id=%s error=%s",
            attempt_id,
            tiger_payment_id,
            exc.message,
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=attempt_id,
            source="api",
            status=str(attempt.get("status") or "pending"),
            payload={
                "action": "confirm_api_failed",
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": omit_qr_images(exc.payload),
            },
            event_key=f"api:confirm_failed:{attempt_id}:{exc.status_code}",
        )
        repos.update_payment_attempt(
            engine,
            attempt_id,
            error_message=exc.message,
            touch_last_polled=True,
        )
        return payment

    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status=normalize_status(str((confirm_result.get("data") or {}).get("status") or "pending")),
        payload={
            "action": "confirm_api_response",
            "confirm_response": omit_qr_images(confirm_result.get("raw") or confirm_result),
        },
        event_key=f"api:confirm_response:{attempt_id}",
    )

    confirmed = confirm_result.get("data")
    if isinstance(confirmed, dict) and (confirmed.get("status") or confirmed.get("id")):
        return confirmed
    try:
        return client.get_payment(tiger_payment_id)
    except TigerPayOpenApiError:
        return payment


def poll_attempt_once(
    engine: Engine,
    attempt: dict[str, Any],
    *,
    open_api: TigerPayOpenApiClient | None = None,
) -> dict[str, Any] | None:
    tiger_payment_id = attempt.get("tiger_payment_id")
    if tiger_payment_id is None:
        return None

    client = open_api or get_open_api_client()
    try:
        payment = client.get_payment(tiger_payment_id)
    except TigerPayOpenApiError as exc:
        logger.warning(
            "Poll failed attempt_id=%s tiger_payment_id=%s error=%s",
            attempt.get("id"),
            tiger_payment_id,
            exc.message,
        )
        repos.update_payment_attempt(
            engine,
            str(attempt["id"]),
            error_message=exc.message,
            touch_last_polled=True,
        )
        return None

    payment = _confirm_qr_if_paid(
        engine,
        attempt=attempt,
        payment=payment,
        client=client,
    )
    return reconcile_from_tiger_payment(
        engine,
        payment,
        source="polling",
        event_key=f"polling:{attempt['id']}:{tiger_payment_id}:{payment.get('status')}:{payment.get('updatedAt')}",
        touch_last_polled=True,
    )


def recover_active_attempts(
    engine: Engine,
    *,
    open_api: TigerPayOpenApiClient | None = None,
) -> list[dict[str, Any]]:
    active = repos.list_active_payment_attempts(engine)
    recovered: list[dict[str, Any]] = []
    for attempt in active:
        updated = poll_attempt_once(engine, attempt, open_api=open_api)
        recovered.append(updated or attempt)
    return recovered
