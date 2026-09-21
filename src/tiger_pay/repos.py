from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.tiger_pay.status import ACTIVE_STATUSES, TERMINAL_STATUSES

ACTIVE_STATUS_SQL = ", ".join(f"'{status}'" for status in sorted(ACTIVE_STATUSES))
TERMINAL_STATUS_SQL = ", ".join(f"'{status}'" for status in sorted(TERMINAL_STATUSES))


def _row_to_attempt(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    amount = mapping.get("amount")
    if isinstance(amount, Decimal):
        mapping["amount"] = float(amount)
    if mapping.get("id") is not None:
        mapping["id"] = str(mapping["id"])
    for key in ("created_at", "updated_at", "last_polled_at"):
        value = mapping.get(key)
        if isinstance(value, datetime):
            mapping[key] = value.isoformat()
    return mapping


def _row_to_event(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    if mapping.get("payment_attempt_id") is not None:
        mapping["payment_attempt_id"] = str(mapping["payment_attempt_id"])
    created_at = mapping.get("created_at")
    if isinstance(created_at, datetime):
        mapping["created_at"] = created_at.isoformat()
    return mapping


def create_payment_attempt(
    engine: Engine,
    *,
    attempt_id: str,
    pos_bill_id: str,
    pos_bill_number: str,
    amount: Decimal | float | int | str,
    status: str,
    raw_status: str | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    if len(attempt_id) > 20:
        raise ValueError("payment attempt id must be <= 20 characters for Tiger RefNo2")

    sql = text(
        """
        insert into tiger_pay.payment_attempt (
            id,
            pos_bill_id,
            pos_bill_number,
            amount,
            status,
            raw_status,
            submitted_by,
            submitted_by_name
        )
        values (
            :id,
            :pos_bill_id,
            :pos_bill_number,
            :amount,
            :status,
            :raw_status,
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
                "id": attempt_id,
                "pos_bill_id": pos_bill_id,
                "pos_bill_number": pos_bill_number,
                "amount": str(amount),
                "status": status,
                "raw_status": raw_status,
                "submitted_by": submitted_by,
                "submitted_by_name": submitted_by_name,
            },
        ).one()
    return _row_to_attempt(row)


def get_payment_attempt(engine: Engine, attempt_id: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where id = :id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": attempt_id}).first()
    return _row_to_attempt(row) if row else None


def get_active_attempt_for_bill(engine: Engine, pos_bill_id: str) -> dict[str, Any] | None:
    sql = text(
        f"""
        select *
        from tiger_pay.payment_attempt
        where pos_bill_id = :pos_bill_id
          and status in ({ACTIVE_STATUS_SQL})
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_attempt(row) if row else None


def get_successful_attempt_for_bill(
    engine: Engine, pos_bill_id: str
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where pos_bill_id = :pos_bill_id
          and status = 'success'
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_attempt(row) if row else None


def list_active_payment_attempts(engine: Engine) -> list[dict[str, Any]]:
    sql = text(
        f"""
        select *
        from tiger_pay.payment_attempt
        where status in ({ACTIVE_STATUS_SQL})
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [_row_to_attempt(row) for row in rows]


def list_unknown_attempts_with_tiger_id(
    engine: Engine,
    *,
    created_after: datetime | None = None,
) -> list[dict[str, Any]]:
    """Stuck rows: Tiger moved to status=change (mapped unknown historically) then success.

    ``created_after`` skips pre-reset device ids so poller does not attach
    recycled Open API ids to July attempts.
    """
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where status = 'unknown'
          and tiger_payment_id is not null
          and (:created_after is null or created_at >= :created_after)
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"created_after": created_after}).all()
    return [_row_to_attempt(row) for row in rows]


def list_sending_without_tiger_id(engine: Engine) -> list[dict[str, Any]]:
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where status = 'sending'
          and tiger_payment_id is null
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [_row_to_attempt(row) for row in rows]


def list_latest_attempts_by_bill_ids(
    engine: Engine,
    pos_bill_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not pos_bill_ids:
        return {}

    sql = text(
        """
        select distinct on (pos_bill_id) *
        from tiger_pay.payment_attempt
        where pos_bill_id = any(:pos_bill_ids)
        order by pos_bill_id, created_at desc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"pos_bill_ids": pos_bill_ids}).all()
    return {_row_to_attempt(row)["pos_bill_id"]: _row_to_attempt(row) for row in rows}


def find_attempt_by_tiger_or_ref(
    engine: Engine,
    *,
    tiger_payment_id: int | None,
    ref_no_2: str | None,
    created_after: datetime | None = None,
) -> dict[str, Any] | None:
    """Match Companion attempt by RefNo2 (attempt id) first, then Tiger id.

    Tiger payment ids were reset on the device; ``created_after`` ignores
    pre-epoch rows when falling back to ``tiger_payment_id``.
    """
    if ref_no_2:
        found = get_payment_attempt(engine, ref_no_2)
        if found:
            return found

    if tiger_payment_id is None:
        return None

    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where tiger_payment_id = :tiger_payment_id
          and (:created_after is null or created_at >= :created_after)
        order by updated_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {
                "tiger_payment_id": tiger_payment_id,
                "created_after": created_after,
            },
        ).first()
    return _row_to_attempt(row) if row else None


def update_payment_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    status: str | None = None,
    raw_status: str | None = None,
    tiger_payment_id: int | None = None,
    tiger_payment_no: str | None = None,
    raw_create_response: dict[str, Any] | None = None,
    error_message: str | None = None,
    touch_last_polled: bool = False,
    clear_error: bool = False,
) -> dict[str, Any] | None:
    sets: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"id": attempt_id}

    if status is not None:
        # Terminal statuses are sticky at the SQL layer so a missed service
        # guard cannot reopen a completed bill.
        sets.append(
            f"""
            status = case
                when status in ({TERMINAL_STATUS_SQL})
                     and status is distinct from :status
                then status
                else :status
            end
            """
        )
        params["status"] = status
    if raw_status is not None:
        sets.append(
            f"""
            raw_status = case
                when status in ({TERMINAL_STATUS_SQL})
                     and :status is not null
                     and status is distinct from :status
                then raw_status
                else :raw_status
            end
            """
        )
        params["raw_status"] = raw_status
        if status is None:
            params["status"] = None
    if tiger_payment_id is not None:
        sets.append("tiger_payment_id = :tiger_payment_id")
        params["tiger_payment_id"] = tiger_payment_id
    if tiger_payment_no is not None:
        sets.append("tiger_payment_no = :tiger_payment_no")
        params["tiger_payment_no"] = tiger_payment_no
    if raw_create_response is not None:
        sets.append("raw_create_response = cast(:raw_create_response as jsonb)")
        params["raw_create_response"] = json.dumps(raw_create_response)
    if error_message is not None:
        sets.append("error_message = :error_message")
        params["error_message"] = error_message
    elif clear_error:
        sets.append("error_message = null")
    if touch_last_polled:
        sets.append("last_polled_at = now()")

    sql = text(
        f"""
        update tiger_pay.payment_attempt
        set {", ".join(sets)}
        where id = :id
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, params).first()
    return _row_to_attempt(row) if row else None


def force_payment_transaction_success(
    engine: Engine,
    tiger_payment_id: int,
    *,
    payment: dict[str, Any] | None = None,
) -> bool:
    """Repair a raced confirm fail so daily totals count the paid QR.

    Only rewrites rows currently in fail/failed (or still carrying the Tiger
    confirm-mismatch remark). Leaves genuine success rows untouched.
    """
    payload_sql = ""
    params: dict[str, Any] = {"tiger_payment_id": tiger_payment_id}
    if payment is not None:
        # Keep shop wrapper if present; otherwise store payment object only.
        payload_sql = ", payload = coalesce(payload, '{}'::jsonb) || cast(:payload as jsonb)"
        params["payload"] = json.dumps({"payment": payment})

    sql = text(
        f"""
        update tiger_pay.payment_transaction
        set
            status = 'success',
            remark = case
                when remark ilike '%does not match the expected value%'
                then null
                else remark
            end
            {payload_sql}
        where tiger_payment_id = :tiger_payment_id
          and (
            lower(status) in ('fail', 'failed')
            or remark ilike '%does not match the expected value%'
          )
        returning tiger_payment_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, params).first()
    return row is not None


def ensure_payment_transaction_success(
    engine: Engine,
    tiger_payment_id: int,
    *,
    amount: Decimal | float | int | str,
    total_pay: Decimal | float | int | str,
    payment_no: str | None = None,
    payment_type: str | None = None,
    payment: dict[str, Any] | None = None,
    remark: str | None = None,
    manual_meta: dict[str, Any] | None = None,
    shop_code: str | None = None,
    ref_no_1: str | None = None,
    ref_no_2: str | None = None,
) -> bool:
    """Upsert payment_transaction as success with explicit money fields.

    Used by admin force-complete so v2 ``qrPromptpayIn`` (total_pay) stays
    correct even when Tiger confirm returns totalPay=0 on an unpaid QR.
    """
    payment_snapshot = dict(payment) if isinstance(payment, dict) else {}
    if payment_snapshot:
        payment_snapshot["status"] = "success"
        payment_snapshot["amount"] = float(amount)
        payment_snapshot["totalPay"] = float(total_pay)
        if payment_no and not payment_snapshot.get("paymentNo"):
            payment_snapshot["paymentNo"] = payment_no
        if payment_type and not payment_snapshot.get("type"):
            payment_snapshot["type"] = payment_type

    payload: dict[str, Any] = {"payment": payment_snapshot} if payment_snapshot else {}
    if manual_meta:
        payload["manual_force"] = {
            **manual_meta,
            "protect_total_pay": True,
        }

    sql = text(
        """
        insert into tiger_pay.payment_transaction as current_payment (
            tiger_payment_id,
            payment_no,
            payment_type,
            status,
            amount,
            total_pay,
            change_amount,
            ref_no_1,
            ref_no_2,
            remark,
            shop_code,
            first_received_at,
            last_received_at,
            payload
        )
        values (
            :tiger_payment_id,
            coalesce(:payment_no, 'MANUAL-' || :tiger_payment_id::text),
            coalesce(:payment_type, 'qr'),
            'success',
            :amount,
            :total_pay,
            0,
            :ref_no_1,
            :ref_no_2,
            :remark,
            :shop_code,
            now(),
            now(),
            cast(:payload as jsonb)
        )
        on conflict (tiger_payment_id)
        do update
        set
            status = 'success',
            amount = excluded.amount,
            total_pay = greatest(
                coalesce(current_payment.total_pay, 0),
                coalesce(excluded.total_pay, 0)
            ),
            payment_no = coalesce(excluded.payment_no, current_payment.payment_no),
            payment_type = coalesce(excluded.payment_type, current_payment.payment_type),
            remark = coalesce(excluded.remark, current_payment.remark),
            ref_no_1 = coalesce(excluded.ref_no_1, current_payment.ref_no_1),
            ref_no_2 = coalesce(excluded.ref_no_2, current_payment.ref_no_2),
            shop_code = coalesce(current_payment.shop_code, excluded.shop_code),
            last_received_at = greatest(current_payment.last_received_at, now()),
            payload = coalesce(current_payment.payload, '{}'::jsonb)
                || cast(:payload as jsonb)
                || jsonb_build_object(
                    'payment',
                    coalesce(current_payment.payload -> 'payment', '{}'::jsonb)
                        || coalesce(cast(:payload as jsonb) -> 'payment', '{}'::jsonb)
                        || jsonb_build_object(
                            'status', 'success',
                            'amount', to_jsonb(excluded.amount),
                            'totalPay', to_jsonb(
                                greatest(
                                    coalesce(current_payment.total_pay, 0),
                                    coalesce(excluded.total_pay, 0)
                                )
                            )
                        )
                )
        returning tiger_payment_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "tiger_payment_id": tiger_payment_id,
                "payment_no": payment_no,
                "payment_type": payment_type,
                "amount": str(amount),
                "total_pay": str(total_pay),
                "remark": remark,
                "shop_code": shop_code,
                "ref_no_1": ref_no_1,
                "ref_no_2": ref_no_2,
                "payload": json.dumps(payload),
            },
        ).first()
    return row is not None


def insert_payment_event(
    engine: Engine,
    *,
    payment_attempt_id: str,
    source: str,
    status: str,
    payload: dict[str, Any] | None = None,
    event_key: str | None = None,
) -> dict[str, Any] | None:
    sql = text(
        """
        insert into tiger_pay.payment_event (
            payment_attempt_id,
            source,
            status,
            payload,
            event_key
        )
        values (
            :payment_attempt_id,
            :source,
            :status,
            cast(:payload as jsonb),
            :event_key
        )
        on conflict (payment_attempt_id, event_key)
            where event_key is not null
            do nothing
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "payment_attempt_id": payment_attempt_id,
                "source": source,
                "status": status,
                "payload": json.dumps(payload or {}),
                "event_key": event_key,
            },
        ).first()
    return _row_to_event(row) if row else None


def list_payment_events(
    engine: Engine,
    payment_attempt_id: str,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select *
        from tiger_pay.payment_event
        where payment_attempt_id = :payment_attempt_id
        order by created_at asc, id asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"payment_attempt_id": payment_attempt_id},
        ).all()
    return [_row_to_event(row) for row in rows]


def latest_webhook_received_at(engine: Engine) -> datetime | None:
    sql = text("select max(received_at) from tiger_pay.webhook_event")
    with engine.connect() as conn:
        value = conn.execute(sql).scalar()
    if isinstance(value, datetime):
        return value
    return None
