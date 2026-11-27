from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

CLOUD_QR_ACTIVE_STATUSES = frozenset({"sending", "I"})
CLOUD_QR_BLOCKING_STATUSES = frozenset({"sending", "I", "C"})
CLOUD_QR_TERMINAL_STATUSES = frozenset({"C", "E", "X", "failed"})

_ACTIVE_SQL = ", ".join(f"'{s}'" for s in sorted(CLOUD_QR_ACTIVE_STATUSES))
_BLOCKING_SQL = ", ".join(f"'{s}'" for s in sorted(CLOUD_QR_BLOCKING_STATUSES))


def is_cloud_qr_active_status(status: str | None) -> bool:
    return str(status or "").strip() in CLOUD_QR_ACTIVE_STATUSES


def is_cloud_qr_blocking_status(status: str | None) -> bool:
    return str(status or "").strip() in CLOUD_QR_BLOCKING_STATUSES


def _row_to_cloud_qr(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    for key in ("amount", "paid_amount"):
        value = mapping.get(key)
        if isinstance(value, Decimal):
            mapping[key] = float(value)
    if mapping.get("id") is not None:
        mapping["id"] = str(mapping["id"])
    for key in ("created_at", "updated_at", "last_polled_at", "paid_at", "announced_at"):
        value = mapping.get(key)
        if isinstance(value, datetime):
            mapping[key] = value.isoformat()
    return mapping


def create_cloud_qr_payment(
    engine: Engine,
    *,
    payment_id: str,
    pos_bill_id: str,
    pos_bill_number: str,
    amount: Decimal | float | int | str,
    status: str = "sending",
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    if len(payment_id) > 20:
        raise ValueError("cloud qr payment id must be <= 20 characters")

    sql = text(
        """
        insert into tiger_pay.cloud_qr_payment (
            id,
            pos_bill_id,
            pos_bill_number,
            amount,
            status,
            submitted_by,
            submitted_by_name
        )
        values (
            :id,
            :pos_bill_id,
            :pos_bill_number,
            :amount,
            :status,
            :submitted_by,
            :submitted_by_name
        )
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "id": payment_id,
                "pos_bill_id": pos_bill_id,
                "pos_bill_number": pos_bill_number,
                "amount": str(amount),
                "status": status,
                "submitted_by": submitted_by,
                "submitted_by_name": submitted_by_name,
            },
        ).one()
    return _row_to_cloud_qr(row)


def get_cloud_qr_payment(engine: Engine, payment_id: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cloud_qr_payment
        where id = :id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": payment_id}).first()
    return _row_to_cloud_qr(row) if row else None


def get_active_cloud_qr_for_bill(
    engine: Engine, pos_bill_id: str
) -> dict[str, Any] | None:
    sql = text(
        f"""
        select *
        from tiger_pay.cloud_qr_payment
        where pos_bill_id = :pos_bill_id
          and status in ({_ACTIVE_SQL})
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_cloud_qr(row) if row else None


def get_successful_cloud_qr_for_bill(
    engine: Engine, pos_bill_id: str
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cloud_qr_payment
        where pos_bill_id = :pos_bill_id
          and status = 'C'
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_cloud_qr(row) if row else None


def get_blocking_cloud_qr_for_bill(
    engine: Engine, pos_bill_id: str
) -> dict[str, Any] | None:
    sql = text(
        f"""
        select *
        from tiger_pay.cloud_qr_payment
        where pos_bill_id = :pos_bill_id
          and status in ({_BLOCKING_SQL})
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_cloud_qr(row) if row else None


def list_latest_cloud_qr_by_bill_ids(
    engine: Engine,
    bill_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not bill_ids:
        return {}
    sql = text(
        """
        select distinct on (pos_bill_id) *
        from tiger_pay.cloud_qr_payment
        where pos_bill_id = any(:bill_ids)
        order by pos_bill_id, created_at desc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"bill_ids": list(bill_ids)}).fetchall()
    return {str(row._mapping["pos_bill_id"]): _row_to_cloud_qr(row) for row in rows}


def list_active_cloud_qr_payments(engine: Engine) -> list[dict[str, Any]]:
    sql = text(
        f"""
        select *
        from tiger_pay.cloud_qr_payment
        where status in ({_ACTIVE_SQL})
          and uuid is not null
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_cloud_qr(row) for row in rows]


def list_cloud_qr_for_window(
    engine: Engine,
    *,
    from_iso: str,
    to_iso: str,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select *
        from tiger_pay.cloud_qr_payment
        where coalesce(paid_at, created_at) >= cast(:from_iso as timestamptz)
          and coalesce(paid_at, created_at) < cast(:to_iso as timestamptz)
        order by coalesce(paid_at, created_at) asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql, {"from_iso": from_iso, "to_iso": to_iso}
        ).fetchall()
    return [_row_to_cloud_qr(row) for row in rows]


def list_successful_cloud_qr_for_biz_day(
    engine: Engine,
    biz_day: date,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select *
        from tiger_pay.cloud_qr_payment
        where status = 'C'
          and (
            (paid_at at time zone 'Asia/Bangkok')::date = :biz_day
            or (
              paid_at is null
              and (created_at at time zone 'Asia/Bangkok')::date = :biz_day
            )
          )
        order by coalesce(paid_at, created_at) asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"biz_day": biz_day}).fetchall()
    return [_row_to_cloud_qr(row) for row in rows]


def update_cloud_qr_payment(
    engine: Engine,
    payment_id: str,
    *,
    status: str | None = None,
    uuid: str | None = None,
    ref1: str | None = None,
    ref2: str | None = None,
    qr_raw_data: str | None = None,
    qr_image: str | None = None,
    payer_name: str | None = None,
    payer_account_number: str | None = None,
    sending_bank_code: str | None = None,
    paid_amount: Decimal | float | int | str | None = None,
    raw_create_response: dict[str, Any] | None = None,
    raw_status_response: dict[str, Any] | None = None,
    error_message: str | None = None,
    clear_error: bool = False,
    touch_polled: bool = False,
    set_paid_at: bool = False,
) -> dict[str, Any] | None:
    sets: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"id": payment_id}

    if status is not None:
        sets.append("status = :status")
        params["status"] = status
    if uuid is not None:
        sets.append("uuid = :uuid")
        params["uuid"] = uuid
    if ref1 is not None:
        sets.append("ref1 = :ref1")
        params["ref1"] = ref1
    if ref2 is not None:
        sets.append("ref2 = :ref2")
        params["ref2"] = ref2
    if qr_raw_data is not None:
        sets.append("qr_raw_data = :qr_raw_data")
        params["qr_raw_data"] = qr_raw_data
    if qr_image is not None:
        sets.append("qr_image = :qr_image")
        params["qr_image"] = qr_image
    if payer_name is not None:
        sets.append("payer_name = :payer_name")
        params["payer_name"] = payer_name
    if payer_account_number is not None:
        sets.append("payer_account_number = :payer_account_number")
        params["payer_account_number"] = payer_account_number
    if sending_bank_code is not None:
        sets.append("sending_bank_code = :sending_bank_code")
        params["sending_bank_code"] = sending_bank_code
    if paid_amount is not None:
        sets.append("paid_amount = :paid_amount")
        params["paid_amount"] = str(paid_amount)
    if raw_create_response is not None:
        sets.append("raw_create_response = cast(:raw_create_response as jsonb)")
        params["raw_create_response"] = json.dumps(raw_create_response)
    if raw_status_response is not None:
        sets.append("raw_status_response = cast(:raw_status_response as jsonb)")
        params["raw_status_response"] = json.dumps(raw_status_response)
    if clear_error:
        sets.append("error_message = null")
    elif error_message is not None:
        sets.append("error_message = :error_message")
        params["error_message"] = error_message
    if touch_polled:
        sets.append("last_polled_at = now()")
    if set_paid_at:
        sets.append("paid_at = coalesce(paid_at, now())")

    sql = text(
        f"""
        update tiger_pay.cloud_qr_payment
        set {", ".join(sets)}
        where id = :id
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, params).first()
    return _row_to_cloud_qr(row) if row else None


def claim_next_cloud_qr_announce(
    engine: Engine,
    *,
    worker_id: str,
    lookback_hours: float = 24.0,
) -> dict[str, Any] | None:
    """Claim one paid cloud QR that has not been announced yet.

    Uses ``FOR UPDATE SKIP LOCKED`` so two till speakers do not double-speak.
    """
    cleaned = str(worker_id or "").strip() or "announce"
    hours = max(0.1, float(lookback_hours))
    sql = text(
        """
        with next_row as (
            select id
            from tiger_pay.cloud_qr_payment
            where status = 'C'
              and announced_at is null
              and coalesce(paid_at, created_at)
                  > now() - (:lookback_hours * interval '1 hour')
            order by coalesce(paid_at, created_at) asc
            for update skip locked
            limit 1
        )
        update tiger_pay.cloud_qr_payment as pay
        set announced_at = now(),
            announced_by = :worker_id,
            updated_at = now()
        from next_row
        where pay.id = next_row.id
        returning pay.*
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {"worker_id": cleaned[:120], "lookback_hours": hours},
        ).first()
    return _row_to_cloud_qr(row) if row else None
