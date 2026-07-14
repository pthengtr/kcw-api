from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.tiger_pay.status import ACTIVE_STATUSES

ACTIVE_STATUS_SQL = ", ".join(f"'{status}'" for status in sorted(ACTIVE_STATUSES))


def _row_to_attempt(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    amount = mapping.get("amount")
    if isinstance(amount, Decimal):
        mapping["amount"] = float(amount)
    for key in ("id",):
        if mapping.get(key) is not None:
            mapping[key] = str(mapping[key])
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
    attempt_id: uuid.UUID,
    pos_bill_id: str,
    pos_bill_number: str,
    amount: Decimal | float | int | str,
    status: str,
    raw_status: str | None = None,
) -> dict[str, Any]:
    sql = text(
        """
        insert into tiger_pay.payment_attempt (
            id,
            pos_bill_id,
            pos_bill_number,
            amount,
            status,
            raw_status
        )
        values (
            :id,
            :pos_bill_id,
            :pos_bill_number,
            :amount,
            :status,
            :raw_status
        )
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "id": str(attempt_id),
                "pos_bill_id": pos_bill_id,
                "pos_bill_number": pos_bill_number,
                "amount": str(amount),
                "status": status,
                "raw_status": raw_status,
            },
        ).one()
    return _row_to_attempt(row)


def get_payment_attempt(engine: Engine, attempt_id: str | uuid.UUID) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where id = :id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": str(attempt_id)}).first()
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
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.payment_attempt
        where (
            :tiger_payment_id is not null
            and tiger_payment_id = :tiger_payment_id
        )
           or (
            :ref_no_2 is not null
            and id::text = :ref_no_2
        )
        order by updated_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {
                "tiger_payment_id": tiger_payment_id,
                "ref_no_2": ref_no_2,
            },
        ).first()
    return _row_to_attempt(row) if row else None


def update_payment_attempt(
    engine: Engine,
    attempt_id: str | uuid.UUID,
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
    params: dict[str, Any] = {"id": str(attempt_id)}

    if status is not None:
        sets.append("status = :status")
        params["status"] = status
    if raw_status is not None:
        sets.append("raw_status = :raw_status")
        params["raw_status"] = raw_status
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


def insert_payment_event(
    engine: Engine,
    *,
    payment_attempt_id: str | uuid.UUID,
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
                "payment_attempt_id": str(payment_attempt_id),
                "source": source,
                "status": status,
                "payload": json.dumps(payload or {}),
                "event_key": event_key,
            },
        ).first()
    return _row_to_event(row) if row else None


def list_payment_events(
    engine: Engine,
    payment_attempt_id: str | uuid.UUID,
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
            {"payment_attempt_id": str(payment_attempt_id)},
        ).all()
    return [_row_to_event(row) for row in rows]
