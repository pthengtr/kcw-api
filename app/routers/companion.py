from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from src.db import get_engine
from src.tiger_pay.payment_service import (
    PaymentServiceError,
    cancel_payment_attempt,
    get_attempt_detail,
    list_bills_with_payment_status,
    send_payment_for_bill,
)
from src.tiger_pay import repos

router = APIRouter(prefix="/companion", tags=["companion"])

_UI_PATH = Path(__file__).resolve().parents[2] / "src" / "companion" / "static" / "index.html"


def _http_error(exc: PaymentServiceError) -> HTTPException:
    status = 400
    if exc.code == "not_found" or exc.code == "bill_not_found":
        status = 404
    elif exc.code in {"active_attempt_exists", "tiger_busy", "not_active"}:
        status = 409
    detail: dict = {"message": exc.message, "code": exc.code}
    if exc.details:
        detail["details"] = exc.details
    return HTTPException(status_code=status, detail=detail)

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def companion_ui() -> HTMLResponse:
    if not _UI_PATH.is_file():
        raise HTTPException(status_code=404, detail="Companion UI not found")
    return HTMLResponse(content=_UI_PATH.read_text(encoding="utf-8"))


@router.get("/bills")
async def companion_bills() -> dict:
    engine = get_engine()
    bills = list_bills_with_payment_status(engine)
    return {"bills": bills}


@router.post("/bills/{pos_bill_id}/pay")
async def companion_pay_bill(pos_bill_id: str) -> dict:
    engine = get_engine()
    try:
        result = send_payment_for_bill(engine, pos_bill_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result


@router.post("/payments/{attempt_id}/cancel")
async def companion_cancel_payment(attempt_id: str) -> dict:
    engine = get_engine()
    try:
        result = cancel_payment_attempt(engine, attempt_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result


@router.get("/payments/active")
async def companion_active_payments() -> dict:
    engine = get_engine()
    attempts = repos.list_active_payment_attempts(engine)
    return {"attempts": attempts}


@router.get("/payments/{attempt_id}")
async def companion_payment_detail(attempt_id: str) -> dict:
    engine = get_engine()
    try:
        result = get_attempt_detail(engine, attempt_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result
