from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.companion.config import get_companion_bill_settings
from src.db import get_engine
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import client_ip, is_tailscale_cg_nat
from src.stock_check.config import get_stock_check_settings
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
SESSION_COOKIE = "kcw_companion_token"


def _line_auth_required() -> bool:
    raw = (os.getenv("COMPANION_REQUIRE_LINE_AUTH") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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


def _verify_companion_token(token: str):
    settings = get_stock_check_settings()
    return verify_access_token(
        token,
        secret=settings.stock_check_token_secret,
        expected_branch=settings.stock_check_branch,
        expected_app="companion",
    )


def _require_companion_user(request: Request) -> None:
    if not _line_auth_required():
        return
    token = request.cookies.get(SESSION_COOKIE) or ""
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"message": "ต้องเปิดลิงก์จาก LINE", "code": "line_auth_required"},
        )
    try:
        _verify_companion_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=401,
            detail={"message": str(exc), "code": "line_auth_invalid"},
        ) from exc


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def companion_ui(request: Request, t: str | None = None) -> HTMLResponse:
    if not _UI_PATH.is_file():
        raise HTTPException(status_code=404, detail="Companion UI not found")

    if _line_auth_required() and t:
        try:
            _verify_companion_token(t)
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
        resp = RedirectResponse(url="/companion/", status_code=303)
        settings = get_stock_check_settings()
        resp.set_cookie(
            SESSION_COOKIE,
            t,
            httponly=True,
            samesite="lax",
            max_age=max(settings.stock_check_token_ttl_seconds, 3600),
        )
        return resp

    if _line_auth_required():
        token = request.cookies.get(SESSION_COOKIE) or ""
        try:
            if not token:
                raise TokenError("missing token")
            _verify_companion_token(token)
        except TokenError:
            if is_tailscale_cg_nat(client_ip(request)):
                settings = get_stock_check_settings()
                minted = mint_access_token(
                    secret=settings.stock_check_token_secret,
                    line_user_id="tailscale",
                    display_name="tailnet",
                    branch=settings.stock_check_branch,
                    ttl_seconds=max(settings.stock_check_token_ttl_seconds, 3600),
                    app="companion",
                )
                resp = RedirectResponse(url="/companion/", status_code=303)
                resp.set_cookie(
                    SESSION_COOKIE,
                    minted,
                    httponly=True,
                    samesite="lax",
                    max_age=max(settings.stock_check_token_ttl_seconds, 3600),
                )
                return resp
            return HTMLResponse(
                "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ ไทเกอร์ หรือ tiger pay ในแชทแล้วกดลิงก์สาขา</p>",
                status_code=401,
            )

    return HTMLResponse(content=_UI_PATH.read_text(encoding="utf-8"))


@router.get("/bills")
async def companion_bills(
    request: Request,
    mode: Literal["latest", "today"] | None = Query(
        default=None,
        description="Override POS_BILLS_MODE for this request (latest or today).",
    ),
    limit: Literal["10", "20", "50", "100", "all"] | None = Query(
        default=None,
        description="Override POS_BILLS_LIMIT for this request (10, 20, 50, 100, or all).",
    ),
) -> dict:
    _require_companion_user(request)
    engine = get_engine()
    try:
        bills = list_bills_with_payment_status(engine, mode=mode, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "code": "bad_query"}) from exc
    settings = get_companion_bill_settings()
    effective_mode = mode or settings.pos_bills_mode
    if limit is not None:
        effective_limit: int | str = "all" if limit == "all" else int(limit)
    else:
        effective_limit = int(settings.pos_bills_limit)
    return {"bills": bills, "mode": effective_mode, "limit": effective_limit}


@router.post("/bills/{pos_bill_id}/pay")
async def companion_pay_bill(request: Request, pos_bill_id: str) -> dict:
    _require_companion_user(request)
    engine = get_engine()
    try:
        result = send_payment_for_bill(engine, pos_bill_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result


@router.post("/payments/{attempt_id}/cancel")
async def companion_cancel_payment(request: Request, attempt_id: str) -> dict:
    _require_companion_user(request)
    engine = get_engine()
    try:
        result = cancel_payment_attempt(engine, attempt_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result


@router.get("/payments/active")
async def companion_active_payments(request: Request) -> dict:
    _require_companion_user(request)
    engine = get_engine()
    attempts = repos.list_active_payment_attempts(engine)
    return {"attempts": attempts}


@router.get("/payments/{attempt_id}")
async def companion_payment_detail(request: Request, attempt_id: str) -> dict:
    _require_companion_user(request)
    engine = get_engine()
    try:
        result = get_attempt_detail(engine, attempt_id)
    except PaymentServiceError as exc:
        raise _http_error(exc) from exc
    return result
