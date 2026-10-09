from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.hq_po.config import get_hq_po_settings
from src.hq_po.guards import HqPoError
from src.hq_po.service import (
    cancel_order,
    confirm_order,
    insight_only_payload,
    list_open_orders,
    suggest_payload,
)
from src.hq_po.ui import APP, SESSION_COOKIE, page
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import is_tailscale_cg_nat

router = APIRouter(prefix="/hq-po", tags=["kcw-hq-po"])


class ConfirmBody(BaseModel):
    vendor: str = ""
    vendor_name: str | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)


class CancelBody(BaseModel):
    reason: str | None = None


def _settings():
    return get_hq_po_settings()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return ""


def _verify_token(token: str):
    settings = _settings()
    return verify_access_token(
        token,
        secret=settings.token_secret,
        expected_branch="HQ",
        expected_app=APP,
    )


def _tokens_from_request(request: Request) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in (request.query_params.get("t"), request.cookies.get(SESSION_COOKIE)):
        token = (raw or "").strip()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _identity_from_request(request: Request):
    for token in _tokens_from_request(request):
        try:
            return _verify_token(token)
        except TokenError:
            continue
    if is_tailscale_cg_nat(_client_ip(request)):
        return None
    return False


def _tailscale_identity():
    from src.stock_check.auth import StockCheckIdentity

    return StockCheckIdentity(
        line_user_id="tailscale",
        display_name="tailnet",
        branch="HQ",
        app=APP,
    )


def _set_session(resp, identity) -> None:
    settings = _settings()
    ttl = max(settings.stock_check_token_ttl_seconds, 86400)
    token = mint_access_token(
        secret=settings.token_secret,
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        ttl_seconds=ttl,
        app=APP,
    )
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=ttl,
        path="/hq-po",
    )


def _require(request: Request):
    settings = _settings()
    if not settings.hq_po_enabled:
        return None, HTMLResponse("hq po disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ สั่งซื้อ ในแชท</p>",
            status_code=401,
        )
    if ident is None:
        ident = _tailscale_identity()
    return ident, None


def _require_api(request: Request):
    ident, err = _require(request)
    if err:
        return None, JSONResponse({"error": "unauthorized"}, status_code=401)
    return ident, None


def _error(exc: HqPoError, status: int = 409):
    return JSONResponse({"error": exc.code, "message": str(exc)}, status_code=status)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    ident, err = _require(request)
    if err and t:
        try:
            ident = _verify_token(t)
            err = None
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
    if err and is_tailscale_cg_nat(_client_ip(request)):
        ident = _tailscale_identity()
        err = None
    if err:
        return err
    settings = _settings()
    html = page(user_name=ident.display_name, stamp_enabled=settings.stamp_enabled)
    if t:
        resp = RedirectResponse(url="/hq-po/", status_code=303)
        _set_session(resp, ident)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "no-store"
    _set_session(resp, ident)
    return resp


@router.get("/api/suggest")
def api_suggest(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return suggest_payload()
    except Exception as exc:
        return JSONResponse({"error": "suggest_failed", "message": str(exc)}, status_code=502)


@router.get("/api/insight")
def api_insight(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return insight_only_payload()
    except Exception as exc:
        return JSONResponse({"error": "insight_failed", "message": str(exc)}, status_code=502)


@router.get("/api/orders")
def api_orders(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return {"orders": list_open_orders()}
    except HqPoError as exc:
        return _error(exc, 503 if exc.code == "supabase_missing" else 409)


@router.post("/api/orders")
def api_confirm(body: ConfirmBody, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        order = confirm_order(
            vendor=body.vendor,
            vendor_name=body.vendor_name,
            lines=body.lines,
            ordered_by=getattr(ident, "display_name", None) or getattr(ident, "line_user_id", None),
        )
    except HqPoError as exc:
        return _error(exc)
    return order


@router.post("/api/orders/{order_id}/cancel")
def api_cancel(order_id: str, body: CancelBody, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return cancel_order(order_id, reason=body.reason)
    except HqPoError as exc:
        return _error(exc)
