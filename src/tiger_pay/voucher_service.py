from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from src.companion.bills import get_open_bill
from src.tiger_pay import voucher_repos
from src.tiger_pay.voucher_api import (
    TigerVoucherApiClient,
    TigerVoucherApiError,
    _looks_like_voucher_num,
    extract_voucher_display,
    extract_voucher_num,
    get_voucher_api_client,
    normalize_voucher_status,
)
from src.tiger_pay.qr import render_qr_image_data_uri
from src.tiger_pay.submitter import normalize_submitter, submitter_payload


logger = logging.getLogger("kcw.tiger_pay.voucher_service")

TIGER_REF_NO2_MAX_LEN = 20


class VoucherServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "voucher_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


def new_voucher_attempt_id() -> str:
    return uuid.uuid4().hex[:TIGER_REF_NO2_MAX_LEN]


def _public_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    return dict(attempt)


def companion_voucher_from_attempt(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    if not attempt:
        return None
    display = extract_voucher_display(attempt.get("raw_create_response") or {})
    show = extract_voucher_display(attempt.get("raw_last_show") or {})
    # Evaluate each candidate with _looks_like_voucher_num — "false" is truthy in Python.
    voucher_num = (
        _looks_like_voucher_num(attempt.get("voucher_num"))
        or _looks_like_voucher_num(show.get("voucher_num"))
        or _looks_like_voucher_num(display.get("voucher_num"))
        or extract_voucher_num(attempt.get("raw_create_response") or {})
        or extract_voucher_num(attempt.get("raw_last_show") or {})
    )
    code = (
        _looks_like_voucher_num(show.get("code"))
        or _looks_like_voucher_num(display.get("code"))
        or voucher_num
    )
    qr_image = show.get("qr_image") or display.get("qr_image")
    qr_raw = (
        _looks_like_voucher_num(show.get("qr_raw"))
        or _looks_like_voucher_num(display.get("qr_raw"))
        or voucher_num
    )
    # Tiger cloud create/show do not return a QR image — render one from the code
    # so Companion can show both a scannable QR and the numeric code.
    if not qr_image and voucher_num:
        try:
            qr_image = render_qr_image_data_uri(str(voucher_num))
        except Exception:
            logger.exception("Failed rendering voucher QR for %s", voucher_num)
            qr_image = None
    return {
        "voucher_num": voucher_num,
        "code": code,
        "qr_image": qr_image,
        "qr_raw": qr_raw,
        "status": attempt.get("status"),
        "raw_status": attempt.get("raw_status"),
    }


def get_voucher_attempt_detail(engine: Engine, attempt_id: str) -> dict[str, Any]:
    attempt = voucher_repos.get_voucher_attempt(engine, attempt_id)
    if not attempt:
        raise VoucherServiceError("Voucher attempt not found", code="not_found")
    if voucher_repos.is_voucher_active_status(str(attempt.get("status"))):
        attempt = refresh_voucher_attempt(engine, attempt_id) or attempt
    events = voucher_repos.list_voucher_events(engine, attempt_id)
    return {
        "attempt": _public_attempt(attempt),
        "events": events,
        "voucher": companion_voucher_from_attempt(attempt),
    }


def create_voucher_for_bill(
    engine: Engine,
    pos_bill_id: str,
    *,
    voucher_api: TigerVoucherApiClient | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    bill = get_open_bill(pos_bill_id)
    if bill is None:
        raise VoucherServiceError("POS bill not found", code="bill_not_found")
    if bill.kind != "payout":
        raise VoucherServiceError(
            "Only cash-return (negative) bills can create vouchers",
            code="not_payout_bill",
        )

    submitted_by, submitted_by_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    submitter = submitter_payload(
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )

    existing = voucher_repos.get_active_voucher_for_bill(engine, pos_bill_id)
    if existing:
        raise VoucherServiceError(
            "Bill already has an active voucher attempt",
            code="active_attempt_exists",
        )

    attempt_id = new_voucher_attempt_id()
    try:
        attempt = voucher_repos.create_voucher_attempt(
            engine,
            attempt_id=attempt_id,
            pos_bill_id=bill.id,
            pos_bill_number=bill.bill_number,
            amount=bill.amount,
            status="creating",
            raw_status="creating",
            ref_num=bill.bill_number,
            submitted_by=submitted_by,
            submitted_by_name=submitted_by_name,
        )
    except IntegrityError as exc:
        raise VoucherServiceError(
            "Bill already has an active voucher attempt",
            code="active_attempt_exists",
        ) from exc

    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status="creating",
        payload={
            "action": "voucher_created",
            "pos_bill_id": bill.id,
            **submitter,
        },
        event_key=f"api:created:{attempt_id}",
    )

    client = voucher_api or get_voucher_api_client()
    amount_value: float | int = float(bill.amount)
    if float(amount_value).is_integer():
        amount_value = int(amount_value)
    try:
        create_result = client.create_voucher(
            amount=amount_value,
            ref_num=bill.bill_number,
            note=f"CN bill {bill.bill_number}",
            category="CN",
        )
    except TigerVoucherApiError as exc:
        voucher_repos.update_voucher_attempt(
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
        voucher_repos.insert_voucher_event(
            engine,
            voucher_attempt_id=attempt_id,
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
        raise VoucherServiceError(
            f"Tiger create voucher failed: {exc.message}",
            code="tiger_create_failed",
            details={"status_code": exc.status_code, "tiger": exc.payload},
        ) from exc

    raw = create_result.get("raw") or create_result
    voucher_num = extract_voucher_num(raw)
    display = extract_voucher_display(raw)
    raw_status = str(display.get("raw_status") or "pending")
    status = normalize_voucher_status(raw_status)
    if status == "unknown":
        status = "pending"

    updated = voucher_repos.update_voucher_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        voucher_num=voucher_num,
        ref_num=bill.bill_number,
        raw_create_response=raw if isinstance(raw, dict) else {"raw": raw},
        clear_error=True,
    )
    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status=status,
        payload={
            "action": "api_response_received",
            "create_response": raw,
            "voucher_num": voucher_num,
        },
        event_key=f"api:create_response:{attempt_id}:{voucher_num or raw_status}",
    )

    stored = updated or attempt
    return {
        "attempt": _public_attempt(stored),
        "create_response": create_result,
        "voucher": companion_voucher_from_attempt(stored),
    }


def refresh_voucher_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    voucher_api: TigerVoucherApiClient | None = None,
) -> dict[str, Any] | None:
    attempt = voucher_repos.get_voucher_attempt(engine, attempt_id)
    if not attempt:
        return None
    if not voucher_repos.is_voucher_active_status(str(attempt.get("status"))):
        return attempt

    voucher_num = attempt.get("voucher_num")
    if not _looks_like_voucher_num(voucher_num):
        # Recover from older create payloads that stored success:"true"/false.
        recovered = extract_voucher_num(attempt.get("raw_create_response") or {})
        if recovered:
            voucher_repos.update_voucher_attempt(
                engine,
                attempt_id,
                voucher_num=recovered,
            )
            voucher_num = recovered
        else:
            return attempt

    client = voucher_api or get_voucher_api_client()
    try:
        show_result = client.show_voucher(str(voucher_num))
    except TigerVoucherApiError as exc:
        logger.warning(
            "voucher show failed attempt_id=%s voucher_num=%s error=%s",
            attempt_id,
            voucher_num,
            exc.message,
        )
        voucher_repos.update_voucher_attempt(
            engine,
            attempt_id,
            touch_last_polled=True,
            error_message=exc.message,
        )
        return voucher_repos.get_voucher_attempt(engine, attempt_id)

    raw = show_result.get("raw") or show_result
    display = extract_voucher_display(raw)
    raw_status = str(display.get("raw_status") or attempt.get("raw_status") or "pending")
    status = normalize_voucher_status(raw_status)
    if status == "unknown":
        status = "pending"

    next_num = display.get("voucher_num") or voucher_num
    if not _looks_like_voucher_num(next_num):
        next_num = voucher_num

    updated = voucher_repos.update_voucher_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        voucher_num=next_num,
        raw_last_show=raw if isinstance(raw, dict) else {"raw": raw},
        touch_last_polled=True,
        clear_error=True,
    )
    if status != str(attempt.get("status")):
        voucher_repos.insert_voucher_event(
            engine,
            voucher_attempt_id=attempt_id,
            source="polling",
            status=status,
            payload={"action": "show_polled", "show_response": raw},
            event_key=f"poll:show:{attempt_id}:{status}:{raw_status}",
        )
    return updated or attempt


def refresh_active_vouchers(engine: Engine) -> None:
    for attempt in voucher_repos.list_active_voucher_attempts(engine):
        try:
            refresh_voucher_attempt(engine, str(attempt["id"]))
        except Exception:
            logger.exception("Failed refreshing voucher attempt %s", attempt.get("id"))


def cancel_voucher_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    voucher_api: TigerVoucherApiClient | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    attempt = voucher_repos.get_voucher_attempt(engine, attempt_id)
    if not attempt:
        raise VoucherServiceError("Voucher attempt not found", code="not_found")
    if not voucher_repos.is_voucher_active_status(str(attempt.get("status"))):
        raise VoucherServiceError("Voucher attempt is not active", code="not_active")

    voucher_num = attempt.get("voucher_num")
    if not _looks_like_voucher_num(voucher_num):
        voucher_num = extract_voucher_num(attempt.get("raw_create_response") or {})
    if not _looks_like_voucher_num(voucher_num):
        raise VoucherServiceError(
            "Voucher number is missing; cannot cancel yet",
            code="missing_voucher_num",
        )

    actor_by, actor_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    actor = submitter_payload(
        submitted_by=actor_by,
        submitted_by_name=actor_name,
    )

    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status="pending",
        payload={"action": "cancellation_requested", **actor},
        event_key=f"api:cancel_requested:{attempt_id}",
    )

    client = voucher_api or get_voucher_api_client()
    try:
        cancel_result = client.cancel_voucher(str(voucher_num))
    except TigerVoucherApiError as exc:
        voucher_repos.update_voucher_attempt(
            engine,
            attempt_id,
            error_message=exc.message,
        )
        voucher_repos.insert_voucher_event(
            engine,
            voucher_attempt_id=attempt_id,
            source="api",
            status="failed",
            payload={
                "action": "cancel_api_failed",
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
            event_key=f"api:cancel_failed:{attempt_id}",
        )
        raise VoucherServiceError(
            f"Tiger cancel voucher failed: {exc.message}",
            code="tiger_cancel_failed",
            details={"status_code": exc.status_code, "tiger": exc.payload},
        ) from exc

    raw = cancel_result.get("raw") or cancel_result
    updated = voucher_repos.update_voucher_attempt(
        engine,
        attempt_id,
        status="cancelled",
        raw_status="cancelled",
        raw_last_show=raw if isinstance(raw, dict) else {"raw": raw},
        clear_error=True,
    )
    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status="cancelled",
        payload={"action": "cancel_api_response", "cancel_response": raw},
        event_key=f"api:cancel_response:{attempt_id}",
    )
    return {
        "attempt": _public_attempt(updated or attempt),
        "cancel_response": cancel_result,
        "voucher": companion_voucher_from_attempt(updated or attempt),
    }
