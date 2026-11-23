"""Tiger cash-in / cash-refund for AR — reuses tiger_pay with ar: / ar-refund: keys."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.db import get_engine
from src.tiger_pay import repos
from src.tiger_pay import voucher_repos
from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError
from src.tiger_pay.payment_service import new_payment_attempt_id, tiger_create_amount
from src.tiger_pay.submitter import normalize_submitter, submitter_payload
from src.tiger_pay.voucher_api import (
    TigerVoucherApiError,
    extract_voucher_display,
    extract_voucher_num,
    get_voucher_api_client,
    normalize_voucher_status,
)
from src.tiger_pay.voucher_service import (
    companion_voucher_from_attempt,
    new_voucher_attempt_id,
    refresh_voucher_attempt,
)


def ar_pos_bill_id(receipt_id: str) -> str:
    rid = (receipt_id or "").strip()
    return f"ar:{rid}"


def ar_refund_pos_bill_id(receipt_id: str) -> str:
    rid = (receipt_id or "").strip()
    return f"ar-refund:{rid}"


def is_ar_pos_bill_id(pos_bill_id: str | None) -> bool:
    raw = str(pos_bill_id or "")
    return raw.startswith("ar:") and not raw.startswith("ar-refund:")


def is_ar_refund_pos_bill_id(pos_bill_id: str | None) -> bool:
    return str(pos_bill_id or "").startswith("ar-refund:")


def receipt_id_from_pos_bill_id(pos_bill_id: str) -> str:
    raw = str(pos_bill_id or "")
    if raw.startswith("ar-refund:"):
        return raw[len("ar-refund:") :]
    if raw.startswith("ar:"):
        return raw[3:]
    return raw


class ReceiveTigerError(RuntimeError):
    def __init__(self, message: str, *, code: str = "tiger_error"):
        super().__init__(message)
        self.code = code


def start_ar_cash_attempt(
    *,
    receipt_id: str,
    amount: float,
    noteno: str | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Send cash portion to Tiger machine. Returns attempt dict.

    ``pos_bill_id`` is ``ar:{receipt_id}`` (unique per overlay receipt / txn).
    Tiger ``ref_no_1`` / ``pos_bill_number`` use the BN/BNN billing-note number
    when provided so the cashbox shows the same reference as ใบวางบิล.
    """
    engine = get_engine()
    pos_bill_id = ar_pos_bill_id(receipt_id)
    note_ref = (noteno or "").strip()
    bill_number = (note_ref or f"AR{(receipt_id or '').replace('-', '')[:12]}")[:40]

    completed = repos.get_successful_attempt_for_bill(engine, pos_bill_id)
    if completed:
        raise ReceiveTigerError(
            "Tiger already succeeded for this receipt", code="already_completed"
        )

    existing = repos.get_active_attempt_for_bill(engine, pos_bill_id)
    if existing:
        raise ReceiveTigerError(
            "Tiger attempt already active for this receipt", code="active_attempt"
        )

    client = TigerPayOpenApiClient()
    try:
        current = client.get_current()
    except TigerPayOpenApiError as exc:
        raise ReceiveTigerError(str(exc), code="tiger_api") from exc
    if current and str(current.get("status") or "").lower() not in (
        "success",
        "fail",
        "cancelled",
        "canceled",
        "",
    ):
        if current.get("id") or current.get("paymentId"):
            raise ReceiveTigerError("Tiger machine is busy", code="tiger_busy")

    floored = tiger_create_amount(amount, payment_type="cash")
    attempt_id = new_payment_attempt_id()
    attempt = repos.create_payment_attempt(
        engine,
        attempt_id=attempt_id,
        pos_bill_id=pos_bill_id,
        pos_bill_number=bill_number,
        amount=Decimal(str(floored)),
        status="sending",
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )

    try:
        created = client.create_payment(
            payment_type="cash",
            amount=floored,
            note=(note or f"AR {bill_number} {receipt_id}")[:100],
            ref_no_1=bill_number,
            ref_no_2=attempt_id,
        )
    except Exception as exc:
        repos.update_payment_attempt(
            engine,
            attempt_id,
            status="failed",
            error_message=str(exc)[:500],
        )
        raise ReceiveTigerError(str(exc), code="tiger_create_failed") from exc

    tiger_payment_id = created.get("id") or created.get("paymentId")
    tiger_payment_no = created.get("paymentNo") or created.get("payment_no")
    raw_status = str(created.get("status") or "pending")
    status = (
        "pending"
        if raw_status.lower() in ("pending", "paying", "changing")
        else raw_status.lower()
    )
    updated = repos.update_payment_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        tiger_payment_id=int(tiger_payment_id) if tiger_payment_id is not None else None,
        tiger_payment_no=str(tiger_payment_no) if tiger_payment_no else None,
        raw_create_response=created,
    )
    return updated or attempt


def get_ar_attempt(receipt_id: str) -> dict[str, Any] | None:
    engine = get_engine()
    pos_bill_id = ar_pos_bill_id(receipt_id)
    active = repos.get_active_attempt_for_bill(engine, pos_bill_id)
    if active:
        return active
    return repos.get_successful_attempt_for_bill(engine, pos_bill_id)


def list_ar_attempts_for_day(received_at: str) -> list[dict[str, Any]]:
    """Best-effort Tiger reconcile list for AR attempts created that calendar day."""
    engine = get_engine()
    sql_day = received_at.strip()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                select *
                from tiger_pay.payment_attempt
                where pos_bill_id like 'ar:%'
                  and pos_bill_id not like 'ar-refund:%'
                  and created_at::date = cast(:day as date)
                order by created_at desc
                """
            ),
            {"day": sql_day},
        ).all()
    return [repos._row_to_attempt(row) for row in rows]  # noqa: SLF001


def start_ar_refund_voucher_attempt(
    *,
    receipt_id: str,
    amount: float,
    noteno: str | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Send cash-refund voucher to Tiger (KCN payout pattern) for an AR overlay receipt.

    ``pos_bill_id`` is ``ar-refund:{receipt_id}``. Tiger ``ref_num`` uses BN/BNN when set.
    Does not write KSS — caller finalizes PVN only after status ``used``.
    """
    engine = get_engine()
    pos_bill_id = ar_refund_pos_bill_id(receipt_id)
    note_ref = (noteno or "").strip()
    bill_number = (note_ref or f"ARRF{(receipt_id or '').replace('-', '')[:10]}")[:40]
    refund_amt = abs(float(amount or 0))
    if refund_amt <= 0:
        raise ReceiveTigerError("refund amount must be > 0", code="validation")

    submitted_by, submitted_by_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    submitter = submitter_payload(
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )

    completed = voucher_repos.get_used_voucher_for_bill(engine, pos_bill_id)
    if completed:
        raise ReceiveTigerError(
            "Tiger refund voucher already completed for this receipt",
            code="already_completed",
        )
    existing = voucher_repos.get_active_voucher_for_bill(engine, pos_bill_id)
    if existing:
        raise ReceiveTigerError(
            "Tiger refund voucher already active for this receipt",
            code="active_attempt",
        )

    attempt_id = new_voucher_attempt_id()
    amount_value: float | int = float(refund_amt)
    if float(amount_value).is_integer():
        amount_value = int(amount_value)

    attempt = voucher_repos.create_voucher_attempt(
        engine,
        attempt_id=attempt_id,
        pos_bill_id=pos_bill_id,
        pos_bill_number=bill_number,
        amount=Decimal(str(refund_amt)),
        status="creating",
        raw_status="creating",
        ref_num=bill_number,
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )
    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status="creating",
        payload={
            "action": "ar_refund_voucher_created",
            "pos_bill_id": pos_bill_id,
            "noteno": note_ref,
            **submitter,
        },
        event_key=f"api:ar_refund_created:{attempt_id}",
    )

    client = get_voucher_api_client()
    try:
        create_result = client.create_voucher(
            amount=amount_value,
            ref_num=bill_number,
            note=(note or f"AR refund {bill_number} {receipt_id}")[:100],
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
            },
            event_key=f"api:ar_refund_create_failed:{attempt_id}",
        )
        raise ReceiveTigerError(
            f"Tiger create refund voucher failed: {exc.message}",
            code="tiger_create_failed",
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
        ref_num=bill_number,
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
            "voucher_num": voucher_num,
            "create_response": raw,
        },
        event_key=f"api:ar_refund_create_response:{attempt_id}:{voucher_num or raw_status}",
    )
    return updated or attempt


def get_ar_refund_attempt(receipt_id: str) -> dict[str, Any] | None:
    engine = get_engine()
    pos_bill_id = ar_refund_pos_bill_id(receipt_id)
    active = voucher_repos.get_active_voucher_for_bill(engine, pos_bill_id)
    if active:
        return active
    return voucher_repos.get_used_voucher_for_bill(engine, pos_bill_id)


def ar_refund_voucher_display(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    """QR + code for staff to scan at Tiger (same shape as KCN companion voucher)."""
    return companion_voucher_from_attempt(attempt)


def refresh_ar_refund_attempt(receipt_id: str) -> dict[str, Any] | None:
    """Poll Tiger voucher show for an AR cash-refund attempt."""
    attempt = get_ar_refund_attempt(receipt_id)
    if not attempt:
        return None
    attempt_id = str(attempt.get("id") or "").strip()
    if not attempt_id:
        return attempt
    if not voucher_repos.is_voucher_active_status(str(attempt.get("status"))):
        return attempt
    return refresh_voucher_attempt(get_engine(), attempt_id) or attempt
