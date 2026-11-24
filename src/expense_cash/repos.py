from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

OPEN_STATUSES = ("pending", "needs_info")
APPROVABLE_STATUSES = ("pending",)


def _row(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    amount = mapping.get("amount")
    if isinstance(amount, Decimal):
        mapping["amount"] = float(amount)
    for key in ("id",):
        if mapping.get(key) is not None:
            mapping[key] = str(mapping[key])
    for key in ("created_at", "updated_at", "reviewed_at"):
        value = mapping.get(key)
        if isinstance(value, datetime):
            mapping[key] = value.isoformat()
    if mapping.get("short_code") is not None:
        mapping["short_code"] = int(mapping["short_code"])
    return mapping


def create_request(
    engine: Engine,
    *,
    requester_line_user_id: str,
    requester_name: str | None,
    reason: str,
    amount: int | float | Decimal,
) -> dict[str, Any]:
    sql = text(
        """
        insert into public.expense_cash_request (
            requester_line_user_id,
            requester_name,
            reason,
            amount,
            status
        )
        values (
            :requester_line_user_id,
            :requester_name,
            :reason,
            :amount,
            'pending'
        )
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(
            sql,
            {
                "requester_line_user_id": requester_line_user_id,
                "requester_name": requester_name,
                "reason": reason,
                "amount": amount,
            },
        ).fetchone()
    assert row is not None
    return _row(row)


def get_by_id(engine: Engine, request_id: str | UUID) -> dict[str, Any] | None:
    sql = text(
        """
        select * from public.expense_cash_request
        where id = cast(:id as uuid)
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": str(request_id)}).fetchone()
    return _row(row) if row else None


def get_by_short_code(engine: Engine, short_code: int) -> dict[str, Any] | None:
    sql = text(
        """
        select * from public.expense_cash_request
        where short_code = :short_code
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"short_code": int(short_code)}).fetchone()
    return _row(row) if row else None


def list_open(engine: Engine, *, limit: int = 20) -> list[dict[str, Any]]:
    sql = text(
        """
        select * from public.expense_cash_request
        where status in ('pending', 'needs_info')
        order by created_at asc
        limit :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).fetchall()
    return [_row(r) for r in rows]


def list_recent(engine: Engine, *, limit: int = 50) -> list[dict[str, Any]]:
    sql = text(
        """
        select * from public.expense_cash_request
        order by created_at desc
        limit :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).fetchall()
    return [_row(r) for r in rows]


def get_open_needs_info_for_user(
    engine: Engine, line_user_id: str
) -> dict[str, Any] | None:
    sql = text(
        """
        select * from public.expense_cash_request
        where requester_line_user_id = :uid
          and status = 'needs_info'
        order by updated_at desc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"uid": line_user_id}).fetchone()
    return _row(row) if row else None


def update_request(
    engine: Engine,
    request_id: str,
    **fields: Any,
) -> dict[str, Any] | None:
    allowed = {
        "reason",
        "extra_reason",
        "amount",
        "status",
        "admin_note",
        "reviewed_by",
        "reviewed_by_name",
        "reviewed_at",
        "voucher_attempt_id",
        "qr_image_url",
    }
    sets: list[str] = []
    params: dict[str, Any] = {"id": request_id}
    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"unsupported field: {key}")
        sets.append(f"{key} = :{key}")
        params[key] = value
    if not sets:
        return get_by_id(engine, request_id)
    sql = text(
        f"""
        update public.expense_cash_request
        set {", ".join(sets)}
        where id = cast(:id as uuid)
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, params).fetchone()
    return _row(row) if row else None


def mark_paid_by_voucher_attempt(
    engine: Engine, voucher_attempt_id: str
) -> dict[str, Any] | None:
    sql = text(
        """
        update public.expense_cash_request
        set status = 'paid'
        where voucher_attempt_id = :vid
          and status = 'approved'
        returning *
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"vid": voucher_attempt_id}).fetchone()
    return _row(row) if row else None


def list_approver_line_ids(engine: Engine) -> list[str]:
    """LINE ids that should receive expense-cash review notifies."""
    from src.expense_cash.approvers import (
        CASH_APPROVER_GROUP,
        CASH_APPROVER_LINE_USER_IDS,
    )

    roster = sorted(CASH_APPROVER_LINE_USER_IDS)
    sql = text(
        """
        select line_user_id
        from ops.line_access
        where is_allowed = true
          and (
            lower(access_group) = :group
            or line_user_id = any(:roster)
          )
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"group": CASH_APPROVER_GROUP, "roster": roster},
        ).fetchall()
    # Preserve stable order: roster first, then any extra cash_approver ids.
    seen: set[str] = set()
    out: list[str] = []
    by_id = {str(r[0]) for r in rows if r[0]}
    for uid in roster:
        if uid in by_id and uid not in seen:
            seen.add(uid)
            out.append(uid)
    for uid in sorted(by_id):
        if uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out
