from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

VOUCHER_ACTIVE_STATUSES = frozenset({"creating", "pending"})
VOUCHER_TERMINAL_STATUSES = frozenset({"used", "cancelled", "expired", "failed"})
VOUCHER_ACTIVE_STATUS_SQL = ", ".join(f"'{status}'" for status in sorted(VOUCHER_ACTIVE_STATUSES))


def is_voucher_active_status(status: str | None) -> bool:
    return str(status or "") in VOUCHER_ACTIVE_STATUSES


def is_voucher_terminal_status(status: str | None) -> bool:
    return str(status or "") in VOUCHER_TERMINAL_STATUSES


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
    if mapping.get("voucher_attempt_id") is not None:
        mapping["voucher_attempt_id"] = str(mapping["voucher_attempt_id"])
    created_at = mapping.get("created_at")
    if isinstance(created_at, datetime):
        mapping["created_at"] = created_at.isoformat()
    return mapping


def create_voucher_attempt(
    engine: Engine,
    *,
    attempt_id: str,
    pos_bill_id: str,
    pos_bill_number: str,
    amount: Decimal | float | int | str,
    status: str,
    raw_status: str | None = None,
    ref_num: str | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    if len(attempt_id) > 20:
        raise ValueError("voucher attempt id must be <= 20 characters")

    sql = text(
        """
        insert into tiger_pay.voucher_attempt (
            id,
            pos_bill_id,
            pos_bill_number,
            amount,
            status,
            raw_status,
            ref_num,
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
            :ref_num,
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
                "ref_num": ref_num,
                "submitted_by": submitted_by,
                "submitted_by_name": submitted_by_name,
            },
        ).one()
    return _row_to_attempt(row)


def get_voucher_attempt(engine: Engine, attempt_id: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.voucher_attempt
        where id = :id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": attempt_id}).first()
    return _row_to_attempt(row) if row else None


def get_active_voucher_for_bill(engine: Engine, pos_bill_id: str) -> dict[str, Any] | None:
    sql = text(
        f"""
        select *
        from tiger_pay.voucher_attempt
        where pos_bill_id = :pos_bill_id
          and status in ({VOUCHER_ACTIVE_STATUS_SQL})
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_attempt(row) if row else None


def get_used_voucher_for_bill(engine: Engine, pos_bill_id: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.voucher_attempt
        where pos_bill_id = :pos_bill_id
          and status = 'used'
        order by created_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pos_bill_id": pos_bill_id}).first()
    return _row_to_attempt(row) if row else None


def list_active_voucher_attempts(engine: Engine) -> list[dict[str, Any]]:
    sql = text(
        f"""
        select *
        from tiger_pay.voucher_attempt
        where status in ({VOUCHER_ACTIVE_STATUS_SQL})
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
    return [_row_to_attempt(row) for row in rows]


def list_latest_vouchers_by_bill_ids(
    engine: Engine,
    pos_bill_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not pos_bill_ids:
        return {}

    sql = text(
        """
        select distinct on (pos_bill_id) *
        from tiger_pay.voucher_attempt
        where pos_bill_id = any(:pos_bill_ids)
        order by pos_bill_id, created_at desc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"pos_bill_ids": pos_bill_ids}).all()
    return {_row_to_attempt(row)["pos_bill_id"]: _row_to_attempt(row) for row in rows}


def update_voucher_attempt(
    engine: Engine,
    attempt_id: str,
    *,
    status: str | None = None,
    raw_status: str | None = None,
    voucher_num: str | None = None,
    ref_num: str | None = None,
    raw_create_response: dict[str, Any] | None = None,
    raw_last_show: dict[str, Any] | None = None,
    error_message: str | None = None,
    touch_last_polled: bool = False,
    clear_error: bool = False,
) -> dict[str, Any] | None:
    sets: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"id": attempt_id}

    if status is not None:
        sets.append("status = :status")
        params["status"] = status
    if raw_status is not None:
        sets.append("raw_status = :raw_status")
        params["raw_status"] = raw_status
    if voucher_num is not None:
        sets.append("voucher_num = :voucher_num")
        params["voucher_num"] = voucher_num
    if ref_num is not None:
        sets.append("ref_num = :ref_num")
        params["ref_num"] = ref_num
    if raw_create_response is not None:
        sets.append("raw_create_response = cast(:raw_create_response as jsonb)")
        params["raw_create_response"] = json.dumps(raw_create_response)
    if raw_last_show is not None:
        sets.append("raw_last_show = cast(:raw_last_show as jsonb)")
        params["raw_last_show"] = json.dumps(raw_last_show)
    if error_message is not None:
        sets.append("error_message = :error_message")
        params["error_message"] = error_message
    elif clear_error:
        sets.append("error_message = null")
    if touch_last_polled:
        sets.append("last_polled_at = now()")

    sql = text(
        f"""
        update tiger_pay.voucher_attempt
        set {", ".join(sets)}
        where id = :id
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, params).first()
    return _row_to_attempt(row) if row else None


def insert_voucher_event(
    engine: Engine,
    *,
    voucher_attempt_id: str,
    source: str,
    status: str,
    payload: dict[str, Any] | None = None,
    event_key: str | None = None,
) -> dict[str, Any] | None:
    sql = text(
        """
        insert into tiger_pay.voucher_event (
            voucher_attempt_id,
            source,
            status,
            payload,
            event_key
        )
        values (
            :voucher_attempt_id,
            :source,
            :status,
            cast(:payload as jsonb),
            :event_key
        )
        on conflict (voucher_attempt_id, event_key)
            where event_key is not null
            do nothing
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "voucher_attempt_id": voucher_attempt_id,
                "source": source,
                "status": status,
                "payload": json.dumps(payload or {}),
                "event_key": event_key,
            },
        ).first()
    return _row_to_event(row) if row else None


def list_voucher_events(
    engine: Engine,
    voucher_attempt_id: str,
) -> list[dict[str, Any]]:
    sql = text(
        """
        select *
        from tiger_pay.voucher_event
        where voucher_attempt_id = :voucher_attempt_id
        order by created_at asc, id asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"voucher_attempt_id": voucher_attempt_id},
        ).all()
    return [_row_to_event(row) for row in rows]
