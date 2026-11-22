"""Tiger cash-in for AR receipts — reuses tiger_pay stack with ar: source keys."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.db import get_engine
from src.tiger_pay import repos
from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError
from src.tiger_pay.payment_service import new_payment_attempt_id, tiger_create_amount


def ar_pos_bill_id(receipt_id: str) -> str:
    rid = (receipt_id or "").strip()
    return f"ar:{rid}"


def is_ar_pos_bill_id(pos_bill_id: str | None) -> bool:
    return str(pos_bill_id or "").startswith("ar:")


def receipt_id_from_pos_bill_id(pos_bill_id: str) -> str:
    raw = str(pos_bill_id or "")
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
                  and created_at::date = cast(:day as date)
                order by created_at desc
                """
            ),
            {"day": sql_day},
        ).all()
    return [repos._row_to_attempt(row) for row in rows]  # noqa: SLF001
