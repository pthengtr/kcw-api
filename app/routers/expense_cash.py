"""Internal HTTP API for kcw-v2 admin cash-request actions."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.db import get_engine
from src.expense_cash import repos
from src.expense_cash.service import (
    ExpenseCashError,
    approve_request,
    cancel_request_voucher,
    refresh_request_voucher,
    reject_request,
    send_back_for_info,
)

router = APIRouter(prefix="/expense-cash", tags=["expense-cash"])


def _require_secret(x_expense_cash_secret: str | None) -> None:
    expected = (os.getenv("EXPENSE_CASH_INTERNAL_SECRET") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="EXPENSE_CASH_INTERNAL_SECRET is not configured",
        )
    if not x_expense_cash_secret or x_expense_cash_secret.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


class ReviewBody(BaseModel):
    note: str | None = None
    reviewer_name: str | None = None
    reviewer_id: str | None = None


@router.get("/requests")
def list_requests(
    x_expense_cash_secret: str | None = Header(default=None),
    limit: int = 50,
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    rows = repos.list_recent(get_engine(), limit=min(limit, 200))
    return {"requests": rows}


@router.get("/requests/{request_id}")
def get_request(
    request_id: str,
    x_expense_cash_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    try:
        return refresh_request_voucher(get_engine(), request_id=request_id)
    except ExpenseCashError as exc:
        raise _http_err(exc) from exc


@router.post("/requests/{request_id}/approve")
def api_approve(
    request_id: str,
    body: ReviewBody | None = None,
    x_expense_cash_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    body = body or ReviewBody()
    try:
        row = approve_request(
            get_engine(),
            request_id=request_id,
            reviewer_line_user_id=body.reviewer_id,
            reviewer_name=body.reviewer_name or "kcw-v2",
        )
    except ExpenseCashError as exc:
        raise _http_err(exc) from exc
    return {"request": row}


@router.post("/requests/{request_id}/needs-info")
def api_needs_info(
    request_id: str,
    body: ReviewBody,
    x_expense_cash_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    try:
        row = send_back_for_info(
            get_engine(),
            request_id=request_id,
            admin_note=body.note or "",
            reviewer_line_user_id=body.reviewer_id,
            reviewer_name=body.reviewer_name or "kcw-v2",
        )
    except ExpenseCashError as exc:
        raise _http_err(exc) from exc
    return {"request": row}


@router.post("/requests/{request_id}/reject")
def api_reject(
    request_id: str,
    body: ReviewBody,
    x_expense_cash_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    try:
        row = reject_request(
            get_engine(),
            request_id=request_id,
            admin_note=body.note or "ปฏิเสธ",
            reviewer_line_user_id=body.reviewer_id,
            reviewer_name=body.reviewer_name or "kcw-v2",
        )
    except ExpenseCashError as exc:
        raise _http_err(exc) from exc
    return {"request": row}


@router.post("/requests/{request_id}/cancel")
def api_cancel(
    request_id: str,
    body: ReviewBody | None = None,
    x_expense_cash_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_secret(x_expense_cash_secret)
    body = body or ReviewBody()
    try:
        row = cancel_request_voucher(
            get_engine(),
            request_id=request_id,
            admin_note=body.note or "ยกเลิก voucher",
            reviewer_line_user_id=body.reviewer_id,
            reviewer_name=body.reviewer_name or "kcw-v2",
        )
    except ExpenseCashError as exc:
        raise _http_err(exc) from exc
    return {"request": row}


def _http_err(exc: ExpenseCashError) -> HTTPException:
    status = 400
    if exc.code == "not_found":
        status = 404
    elif exc.code in {
        "tiger_create_failed",
        "qr_upload_failed",
        "supabase_missing",
        "tiger_cancel_failed",
        "tiger_cancel_unconfirmed",
    }:
        status = 502
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})
