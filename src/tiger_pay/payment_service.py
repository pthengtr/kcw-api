from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, InvalidOperation
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from src.companion.bills import get_open_bill, list_cn_bills, list_open_bills
from src.tiger_pay import repos
from src.tiger_pay import voucher_repos
from src.tiger_pay.config import get_tiger_pay_settings, parse_payment_id_epoch
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
from src.tiger_pay.status import can_replace_status, is_active_status, normalize_status
from src.tiger_pay.submitter import normalize_submitter, submitter_payload
from src.tiger_pay.voucher_repos import is_voucher_active_status
from src.tiger_pay.voucher_service import (
    companion_voucher_from_attempt,
    schedule_refresh_active_vouchers,
)

logger = logging.getLogger("kcw.tiger_pay.payment_service")

# Tiger Open API: RefNo2 max length is 20.
TIGER_REF_NO2_MAX_LEN = 20
ALLOWED_PAYMENT_TYPES = frozenset({"cash", "qr"})


def new_payment_attempt_id() -> str:
    """Generate an internal attempt id that fits Tiger RefNo2 (<=20)."""
    return uuid.uuid4().hex[:TIGER_REF_NO2_MAX_LEN]


def tiger_create_amount(
    amount: Decimal | float | int | str,
    *,
    payment_type: str,
) -> int | float:
    """Amount sent to Tiger create-payment.

    Cash Open API rejects fractional baht (``value.amount`` 400). Floor cash
    to a whole baht; keep QR decimals when present.
    """
    value = Decimal(str(amount))
    if payment_type == "cash":
        floored = int(value.to_integral_value(rounding=ROUND_FLOOR))
        if floored <= 0:
            raise PaymentServiceError(
                "Cash amount must be at least 1 baht after rounding down",
                code="invalid_cash_amount",
                details={"amount": str(amount), "floored": floored},
            )
        return floored
    amount_value: float | int = float(value)
    if float(amount_value).is_integer():
        return int(amount_value)
    return amount_value


def tiger_amount_compatible(attempt: dict[str, Any], payment: dict[str, Any]) -> bool:
    """True when a Tiger success may be applied to this attempt.

    Cash satang is floored on create (vendor limit, accepted). QR must match
    the POS amount to 2 decimals. Missing amounts skip the check.
    """
    raw_tiger = payment.get("amount")
    raw_pos = attempt.get("amount")
    if raw_tiger is None or raw_tiger == "" or raw_pos is None or raw_pos == "":
        return True
    try:
        tiger = Decimal(str(raw_tiger))
        pos = Decimal(str(raw_pos))
    except (InvalidOperation, TypeError, ValueError):
        return True

    pay_type = str(
        payment.get("type") or payment.get("payment_type") or payment_type_from_attempt(attempt) or "cash"
    ).strip().lower()
    if pay_type in {"qr", "promptpay"}:
        quantum = Decimal("0.01")
        return tiger.quantize(quantum) == pos.quantize(quantum)

    floored = pos.to_integral_value(rounding=ROUND_FLOOR)
    return tiger == floored or tiger == pos


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


class _ThreadResult:
    """Run ``fn`` on a worker thread; ``result()`` joins and returns or raises."""

    def __init__(self, fn) -> None:
        self._error: BaseException | None = None
        self._value: Any = None
        self._thread = threading.Thread(target=self._run, args=(fn,), daemon=True)
        self._thread.start()

    def _run(self, fn) -> None:
        try:
            self._value = fn()
        except BaseException as exc:
            self._error = exc

    def result(self) -> Any:
        self._thread.join()
        if self._error is not None:
            raise self._error
        return self._value


def _join_ignored(job: _ThreadResult | None) -> None:
    if job is None:
        return
    try:
        job.result()
    except Exception:
        logger.debug("background Tiger get_current finished with error", exc_info=True)


def list_bills_with_payment_status(
    engine: Engine,
    *,
    mode: str | None = None,
    limit: int | str | None = None,
) -> list[dict[str, Any]]:
    # Refresh pending CN vouchers in the background. Tiger cloud show/login is
    # often multi-second; blocking here made /companion/bills feel stuck while
    # the UI polls every ~1.5s with an active attempt.
    try:
        schedule_refresh_active_vouchers(engine)
    except Exception:
        logger.exception("Failed scheduling active voucher refresh before bill list")

    collect_bills = list_open_bills(mode=mode, limit=limit)
    payout_bills = list_cn_bills(mode=mode, limit=limit)
    bills = [*collect_bills, *payout_bills]

    latest_by_bill = repos.list_latest_attempts_by_bill_ids(
        engine,
        [bill.id for bill in collect_bills],
    )
    try:
        latest_vouchers = voucher_repos.list_latest_vouchers_by_bill_ids(
            engine,
            [bill.id for bill in payout_bills],
        )
    except Exception:
        # Keep collect bills usable if voucher tables are not migrated yet.
        logger.exception("Failed loading voucher attempts for bill list")
        latest_vouchers = {}
    results: list[dict[str, Any]] = []
    for bill in bills:
        item = bill.to_dict()
        if bill.kind == "payout":
            attempt = latest_vouchers.get(bill.id)
            item["tiger_payment_status"] = attempt["status"] if attempt else None
            item["tiger_payment_no"] = attempt.get("voucher_num") if attempt else None
            item["tiger_payment_id"] = None
            item["payment_attempt_id"] = attempt["id"] if attempt else None
            item["payment_attempt_active"] = bool(
                attempt and is_voucher_active_status(str(attempt["status"]))
            )
            item["payment_type"] = "voucher"
            item["voucher"] = companion_voucher_from_attempt(attempt)
            item["submitted_by"] = attempt.get("submitted_by") if attempt else None
            item["submitted_by_name"] = attempt.get("submitted_by_name") if attempt else None
        else:
            attempt = latest_by_bill.get(bill.id)
            item["tiger_payment_status"] = attempt["status"] if attempt else None
            item["tiger_payment_no"] = attempt["tiger_payment_no"] if attempt else None
            item["tiger_payment_id"] = attempt["tiger_payment_id"] if attempt else None
            item["payment_attempt_id"] = attempt["id"] if attempt else None
            item["payment_attempt_active"] = bool(
                attempt and is_active_status(str(attempt["status"]))
            )
            item["payment_type"] = payment_type_from_attempt(attempt) if attempt else None
            item["voucher"] = None
            item["submitted_by"] = attempt.get("submitted_by") if attempt else None
            item["submitted_by_name"] = attempt.get("submitted_by_name") if attempt else None
        results.append(item)

    results.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    # Collect + CN each use TOP(limit); without a combined cap the UI dropdown
    # (e.g. 10) can show ~2× that many rows.
    cap = _combined_bills_cap(limit)
    if cap is not None:
        results = results[:cap]
    return results


def _combined_bills_cap(limit: int | str | None) -> int | None:
    """Max rows for the merged companion list, or None when unlimited."""
    if limit is None:
        from src.companion.config import get_companion_bill_settings

        return max(1, int(get_companion_bill_settings().pos_bills_limit))
    if isinstance(limit, str) and limit.strip().lower() == "all":
        return None
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _public_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    attempt_out = dict(attempt)
    if attempt_out.get("raw_create_response") is not None:
        attempt_out["raw_create_response"] = omit_qr_images(attempt_out["raw_create_response"])
    return attempt_out


def get_attempt_detail(engine: Engine, attempt_id: str) -> dict[str, Any]:
    attempt = repos.get_payment_attempt(engine, attempt_id)
    if not attempt:
        raise PaymentServiceError("Payment attempt not found", code="not_found")
    events = repos.list_payment_events(engine, attempt_id)
    return {
        "attempt": _public_attempt(attempt),
        "events": events,
        "qr": companion_qr_from_attempt(attempt),
        "payment_type": payment_type_from_attempt(attempt),
    }


def send_payment_for_bill(
    engine: Engine,
    pos_bill_id: str,
    *,
    payment_type: str = "cash",
    open_api: TigerPayOpenApiClient | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    cleaned_type = str(payment_type or "cash").strip().lower()
    if cleaned_type not in ALLOWED_PAYMENT_TYPES:
        raise PaymentServiceError(
            "payment_type must be cash or qr",
            code="invalid_payment_type",
        )
    submitted_by, submitted_by_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    submitter = submitter_payload(
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )

    client = open_api or get_open_api_client()
    current_job = _ThreadResult(client.get_current)
    try:
        bill = get_open_bill(pos_bill_id)
        if bill is None:
            raise PaymentServiceError("POS bill not found", code="bill_not_found")
        if bill.kind == "payout":
            raise PaymentServiceError(
                "CN payout bills use voucher cash-return, not payment",
                code="not_collect_bill",
            )
        # Legacy POS PAID is display-only — Tiger payment_attempt is the source of truth.
        completed = repos.get_successful_attempt_for_bill(engine, pos_bill_id)
        if completed:
            raise PaymentServiceError(
                "Bill already has a completed payment",
                code="payment_already_completed",
            )

        existing = repos.get_active_attempt_for_bill(engine, pos_bill_id)
        if existing:
            raise PaymentServiceError(
                "Bill already has an active payment attempt",
                code="active_attempt_exists",
            )

        try:
            current = current_job.result()
        except TigerPayOpenApiError as exc:
            raise PaymentServiceError(
                f"Unable to check Tiger current payment: {exc.message}",
                code="tiger_current_failed",
            ) from exc
        current_job = None

        if current is not None:
            raise PaymentServiceError(
                "Tiger Pay already has an active payment",
                code="tiger_busy",
            )
    finally:
        _join_ignored(current_job)

    # Validate/normalize Tiger amount before opening an attempt row.
    amount_value = tiger_create_amount(bill.amount, payment_type=cleaned_type)

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
            submitted_by=submitted_by,
            submitted_by_name=submitted_by_name,
        )
    except IntegrityError as exc:
        if repos.get_successful_attempt_for_bill(engine, pos_bill_id):
            raise PaymentServiceError(
                "Bill already has a completed payment",
                code="payment_already_completed",
            ) from exc
        raise PaymentServiceError(
            "Bill already has an active payment attempt",
            code="active_attempt_exists",
        ) from exc

    repos.insert_payment_event(
        engine,
        payment_attempt_id=attempt_id,
        source="api",
        status="sending",
        payload={
            "action": "payment_created",
            "pos_bill_id": bill.id,
            "tiger_amount": amount_value,
            **submitter,
        },
        event_key=f"api:created:{attempt_id}",
    )

    note = f"POS bill {bill.bill_number}"
    try:
        create_kwargs: dict[str, Any] = {
            "amount": amount_value,
            "ref_no_1": bill.bill_number,
            "ref_no_2": str(attempt_id),
            "note": note,
            "payment_type": cleaned_type,
        }
        # Device defaults type=qr to SCB; SCB is disabled — force KBANK.
        if cleaned_type == "qr":
            create_kwargs["payment_gateway"] = get_tiger_pay_settings().tiger_pay_qr_gateway
        create_result = client.create_payment(**create_kwargs)
        create_result = _ensure_qr_on_create(
            client,
            create_result,
            payment_type=cleaned_type,
        )
    except TigerPayOpenApiError as exc:
        if exc.no_response:
            repos.insert_payment_event(
                engine,
                payment_attempt_id=attempt_id,
                source="api",
                status="sending",
                payload={
                    "action": "create_unconfirmed",
                    "error": exc.message,
                    "status_code": exc.status_code,
                    "payload": exc.payload,
                },
                event_key=f"api:create_unconfirmed:{attempt_id}",
            )
            raise PaymentServiceError(
                f"Tiger create payment unconfirmed: {exc.message}",
                code="tiger_create_unconfirmed",
                details={"status_code": exc.status_code, "tiger": exc.payload},
            ) from exc
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

    stored = updated or attempt
    return {
        "attempt": _public_attempt(stored),
        "create_response": omit_qr_images(create_result),
        "qr": extract_companion_qr(create_result.get("raw") or create_result),
        "payment_type": cleaned_type,
    }


def cancel_payment_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    open_api: TigerPayOpenApiClient | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
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

    actor_by, actor_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    actor = submitter_payload(
        submitted_by=actor_by,
        submitted_by_name=actor_name,
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
        payload={"action": "cancellation_requested", **actor},
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
        created_after=parse_payment_id_epoch(get_tiger_pay_settings().tiger_pay_id_epoch),
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
    incoming = normalize_status(raw_status)
    payment_no = payment.get("paymentNo") or payment.get("payment_no") or attempt.get(
        "tiger_payment_no"
    )
    key = event_key or f"{source}:{attempt['id']}:{tiger_payment_id}:{raw_status}"
    current_status = str(attempt.get("status") or "")

    if not can_replace_status(current_status, incoming):
        logger.warning(
            "Ignoring %s status downgrade attempt_id=%s current=%s incoming=%s",
            source,
            attempt["id"],
            current_status,
            incoming,
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=str(attempt["id"]),
            source=source,
            status=current_status,
            payload={
                "action": f"{source}_ignored_downgrade",
                "current_status": current_status,
                "incoming_status": incoming,
                "payment": omit_qr_images(payment),
            },
            event_key=f"{key}:ignored",
        )
        return repos.update_payment_attempt(
            engine,
            str(attempt["id"]),
            tiger_payment_id=None,
            touch_last_polled=touch_last_polled,
        )

    if incoming == "success" and not tiger_amount_compatible(attempt, payment):
        logger.warning(
            "Ignoring %s success amount mismatch attempt_id=%s pos=%s tiger=%s type=%s",
            source,
            attempt["id"],
            attempt.get("amount"),
            payment.get("amount"),
            payment.get("type") or payment.get("payment_type"),
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=str(attempt["id"]),
            source=source,
            status=current_status,
            payload={
                "action": f"{source}_amount_mismatch",
                "pos_amount": str(attempt.get("amount")),
                "tiger_amount": payment.get("amount"),
                "payment": omit_qr_images(payment),
            },
            event_key=f"{key}:amount_mismatch",
        )
        return repos.update_payment_attempt(
            engine,
            str(attempt["id"]),
            error_message="tiger amount mismatch; success not applied",
            touch_last_polled=touch_last_polled,
        )

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
        "amount": transaction.get("amount"),
        "totalPay": transaction.get("total_pay"),
        "type": transaction.get("payment_type"),
        "payment_type": transaction.get("payment_type"),
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


def recover_sending_attempts(
    engine: Engine,
    *,
    open_api: TigerPayOpenApiClient | None = None,
) -> list[dict[str, Any]]:
    """Attach or fail `sending` rows that never got a Tiger payment id."""
    settings = get_tiger_pay_settings()
    stale_after = float(settings.tiger_pay_sending_stale_seconds)
    client = open_api or get_open_api_client()
    recovered: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for attempt in repos.list_sending_without_tiger_id(engine):
        attempt_id = str(attempt.get("id") or "")
        if not attempt_id:
            continue
        payment: dict[str, Any] | None = None
        try:
            payment = client.find_payment_by_ref_no_2(attempt_id)
        except TigerPayOpenApiError as exc:
            logger.warning(
                "Sending recovery lookup failed attempt_id=%s error=%s",
                attempt_id,
                exc.message,
            )
        if payment:
            updated = reconcile_from_tiger_payment(
                engine,
                payment,
                source="polling",
                event_key=f"polling:recover:{attempt_id}:{payment.get('id')}:{payment.get('status')}",
                touch_last_polled=True,
            )
            recovered.append(updated or attempt)
            continue

        created_raw = attempt.get("created_at")
        created_at: datetime | None = None
        if isinstance(created_raw, datetime):
            created_at = created_raw
        elif isinstance(created_raw, str):
            try:
                created_at = datetime.fromisoformat(created_raw)
            except ValueError:
                created_at = None
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age = (now - created_at).total_seconds() if created_at is not None else 0.0
        if age < stale_after:
            recovered.append(attempt)
            continue

        repos.update_payment_attempt(
            engine,
            attempt_id,
            status="failed",
            raw_status="failed",
            error_message="create unconfirmed; marked failed after stale timeout",
            touch_last_polled=True,
        )
        repos.insert_payment_event(
            engine,
            payment_attempt_id=attempt_id,
            source="polling",
            status="failed",
            payload={"action": "create_unconfirmed_expired", "age_seconds": age},
            event_key=f"polling:create_unconfirmed_expired:{attempt_id}",
        )
        recovered.append(repos.get_payment_attempt(engine, attempt_id) or attempt)
    return recovered


def recover_active_attempts(
    engine: Engine,
    *,
    open_api: TigerPayOpenApiClient | None = None,
) -> list[dict[str, Any]]:
    epoch = parse_payment_id_epoch(get_tiger_pay_settings().tiger_pay_id_epoch)
    to_poll = [
        *repos.list_active_payment_attempts(engine),
        *repos.list_unknown_attempts_with_tiger_id(engine, created_after=epoch),
    ]
    seen: set[str] = set()
    recovered: list[dict[str, Any]] = []
    for attempt in to_poll:
        attempt_id = str(attempt.get("id") or "")
        if not attempt_id or attempt_id in seen:
            continue
        seen.add(attempt_id)
        updated = poll_attempt_once(engine, attempt, open_api=open_api)
        recovered.append(updated or attempt)
    recovered.extend(recover_sending_attempts(engine, open_api=open_api))
    return recovered
