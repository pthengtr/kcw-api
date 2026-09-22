from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.tiger_pay.normalize import BANGKOK_TZ


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _row_mapping(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    return {key: _json_value(val) for key, val in mapping.items()}


def insert_cash_snapshot(
    engine: Engine,
    *,
    captured_at: datetime,
    biz_day: date,
    trigger: str,
    shop_code: str,
    change_ready: bool | None,
    change_level: str,
    change_reasons: list[str],
    items: list[dict[str, Any]],
    total_baht: Decimal | float | int,
    cash_box_items: list[dict[str, Any]] | None = None,
    cash_box_total_baht: Decimal | float | int = 0,
    tiger_payment_id: int | None = None,
    payment_no: str | None = None,
    payment_status: str | None = None,
) -> dict[str, Any]:
    sql = text(
        """
        insert into tiger_pay.cash_snapshot (
            captured_at,
            biz_day,
            trigger,
            tiger_payment_id,
            payment_no,
            payment_status,
            change_ready,
            change_level,
            change_reasons,
            items,
            total_baht,
            cash_box_items,
            cash_box_total_baht,
            shop_code
        )
        values (
            :captured_at,
            :biz_day,
            :trigger,
            :tiger_payment_id,
            :payment_no,
            :payment_status,
            :change_ready,
            :change_level,
            cast(:change_reasons as jsonb),
            cast(:items as jsonb),
            :total_baht,
            cast(:cash_box_items as jsonb),
            :cash_box_total_baht,
            :shop_code
        )
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "captured_at": captured_at,
                "biz_day": biz_day,
                "trigger": trigger,
                "tiger_payment_id": tiger_payment_id,
                "payment_no": payment_no,
                "payment_status": payment_status,
                "change_ready": change_ready,
                "change_level": change_level,
                "change_reasons": json.dumps(change_reasons),
                "items": json.dumps(items),
                "total_baht": str(total_baht),
                "cash_box_items": json.dumps(cash_box_items or []),
                "cash_box_total_baht": str(cash_box_total_baht),
                "shop_code": shop_code,
            },
        ).one()
    return _row_mapping(row)


def latest_cash_snapshot(engine: Engine, shop_code: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cash_snapshot
        where shop_code = :shop_code
        order by captured_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"shop_code": shop_code}).first()
    return _row_mapping(row) if row else None


def recent_snapshot_for_payment(
    engine: Engine,
    *,
    tiger_payment_id: int,
    payment_status: str,
    within_seconds: float = 2.0,
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cash_snapshot
        where tiger_payment_id = :tiger_payment_id
          and payment_status = :payment_status
          and captured_at >= now() - make_interval(secs => :within_seconds)
        order by captured_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {
                "tiger_payment_id": tiger_payment_id,
                "payment_status": payment_status,
                "within_seconds": within_seconds,
            },
        ).first()
    return _row_mapping(row) if row else None


def get_daily_close(
    engine: Engine, *, biz_day: date, shop_code: str
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.daily_close
        where biz_day = :biz_day
          and shop_code = :shop_code
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql, {"biz_day": biz_day, "shop_code": shop_code}
        ).first()
    return _row_mapping(row) if row else None


def previous_closing_snapshot_id(
    engine: Engine, *, biz_day: date, shop_code: str
) -> str | None:
    sql = text(
        """
        select closing_snapshot_id
        from tiger_pay.daily_close
        where shop_code = :shop_code
          and biz_day < :biz_day
        order by biz_day desc
        limit 1
        """
    )
    with engine.connect() as conn:
        value = conn.execute(
            sql, {"shop_code": shop_code, "biz_day": biz_day}
        ).scalar()
    return str(value) if value else None


def get_snapshot_by_id(engine: Engine, snapshot_id: str) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cash_snapshot
        where id = :id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": snapshot_id}).first()
    return _row_mapping(row) if row else None


def first_snapshot_of_day(
    engine: Engine, *, biz_day: date, shop_code: str
) -> dict[str, Any] | None:
    sql = text(
        """
        select *
        from tiger_pay.cash_snapshot
        where shop_code = :shop_code
          and biz_day = :biz_day
        order by captured_at asc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql, {"shop_code": shop_code, "biz_day": biz_day}
        ).first()
    return _row_mapping(row) if row else None


def insert_daily_close(
    engine: Engine,
    *,
    biz_day: date,
    shop_code: str,
    trigger: str,
    opening_snapshot_id: str | None,
    closing_snapshot_id: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    sql = text(
        """
        insert into tiger_pay.daily_close (
            biz_day,
            shop_code,
            trigger,
            opening_snapshot_id,
            closing_snapshot_id,
            report
        )
        values (
            :biz_day,
            :shop_code,
            :trigger,
            :opening_snapshot_id,
            :closing_snapshot_id,
            cast(:report as jsonb)
        )
        on conflict (biz_day, shop_code) do nothing
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "biz_day": biz_day,
                "shop_code": shop_code,
                "trigger": trigger,
                "opening_snapshot_id": opening_snapshot_id,
                "closing_snapshot_id": closing_snapshot_id,
                "report": json.dumps(report),
            },
        ).first()
    if row:
        return _row_mapping(row)
    existing = get_daily_close(engine, biz_day=biz_day, shop_code=shop_code)
    if existing is None:
        raise RuntimeError("daily_close insert failed")
    return existing


def list_payment_transactions_for_day(
    engine: Engine, *, biz_day: date, shop_code: str
) -> list[dict[str, Any]]:
    sql = text(
        """
        select
            tiger_payment_id,
            payment_no,
            payment_type,
            status,
            amount,
            total_pay,
            change_amount,
            shop_code,
            tiger_created_at,
            last_received_at,
            payload,
            note,
            remark
        from tiger_pay.payment_transaction
        where (timezone('Asia/Bangkok', coalesce(tiger_created_at, last_received_at)))::date
              = :biz_day
          and shop_code = :shop_code
        order by coalesce(tiger_created_at, last_received_at) asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql, {"biz_day": biz_day, "shop_code": shop_code}
        ).all()
    return [_row_mapping(row) for row in rows]


def list_voucher_attempts_for_day(
    engine: Engine, *, biz_day: date
) -> list[dict[str, Any]]:
    sql = text(
        """
        select id, pos_bill_number, amount, status, created_at
        from tiger_pay.voucher_attempt
        where timezone('Asia/Bangkok', created_at)::date = :biz_day
        order by created_at asc
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"biz_day": biz_day}).all()
    return [_row_mapping(row) for row in rows]


def claim_next_cash_command(engine: Engine) -> dict[str, Any] | None:
    sql = text(
        """
        with next_cmd as (
            select id
            from tiger_pay.cash_command
            where status = 'pending'
            order by requested_at asc
            for update skip locked
            limit 1
        )
        update tiger_pay.cash_command as cmd
        set status = 'running',
            started_at = now()
        from next_cmd
        where cmd.id = next_cmd.id
        returning cmd.*
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql).first()
    return _row_mapping(row) if row else None


def finish_cash_command(
    engine: Engine,
    command_id: str,
    *,
    status: str,
    error: str | None = None,
    snapshot_id: str | None = None,
) -> None:
    sql = text(
        """
        update tiger_pay.cash_command
        set status = :status,
            finished_at = now(),
            error = :error,
            snapshot_id = coalesce(:snapshot_id, snapshot_id)
        where id = :id
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id": command_id,
                "status": status,
                "error": error,
                "snapshot_id": snapshot_id,
            },
        )


def bangkok_biz_day(now: datetime | None = None) -> date:
    current = now or datetime.now(BANGKOK_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BANGKOK_TZ)
    return current.astimezone(BANGKOK_TZ).date()
