from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.online_sale.config import get_online_sale_settings
from src.online_sale.errors import OnlineSaleError
from src.online_sale.net import is_private_lan
from src.online_sale.service import (
    bill_payload,
    check_po_payload,
    meta_payload,
    print_cntad_html,
    print_tad_html,
    product_payload,
    return_preview_payload,
    save_return_payload,
    save_sale_payload,
    search_payload,
    shops_payload,
)
from src.online_sale.ui import APP, SESSION_COOKIE, page
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import is_tailscale_cg_nat
from src.to_bill.ui import APP as TO_APP
from src.to_bill.ui import SESSION_COOKIE as TO_SESSION_COOKIE

router = APIRouter(prefix="/online-sale", tags=["kcw-online-sale"])


class SaleBody(BaseModel):
    acctno: str = ""
    online_po: str = ""
    allow_oversell: bool = False
    lines: list[dict[str, Any]] = Field(default_factory=list)


class CheckPoBody(BaseModel):
    acctno: str = ""
    online_po: str = ""


class ReturnBody(BaseModel):
    tad_billno: str = ""
    reason_id: str = ""
    reason_note: str = ""
    lines: list[dict[str, Any]] = Field(default_factory=list)


def _settings():
    return get_online_sale_settings()


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


def _named(line_user_id: str, display_name: str):
    from src.stock_check.auth import StockCheckIdentity

    return StockCheckIdentity(
        line_user_id=line_user_id,
        display_name=display_name,
        branch="HQ",
        app=APP,
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
    ip = _client_ip(request)
    if is_tailscale_cg_nat(ip):
        return _named("tailscale", "tailnet")
    if is_private_lan(ip):
        return _named("lan", "LAN")
    return None


def _set_session(resp, identity) -> None:
    """Mint cookies for online-sale and merged to-bill on the same host."""
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
        path="/online-sale",
    )
    to_token = mint_access_token(
        secret=settings.token_secret,
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        ttl_seconds=ttl,
        app=TO_APP,
    )
    resp.set_cookie(
        TO_SESSION_COOKIE,
        to_token,
        httponly=True,
        samesite="lax",
        max_age=ttl,
        path="/to-bill",
    )


def _actor(identity) -> str:
    name = (identity.display_name or identity.line_user_id or "").strip()
    return name[:80] or "unknown"


def _require(request: Request):
    settings = _settings()
    if not settings.online_sale_enabled:
        return None, HTMLResponse("online sale disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is None:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ ขายออนไลน์ ในแชท หรือเปิดจากเครือข่ายสำนักงานใหญ่</p>",
            status_code=401,
        )
    return ident, None


def _require_api(request: Request):
    ident, err = _require(request)
    if err is not None:
        if isinstance(err, HTMLResponse):
            return None, JSONResponse(
                {"error": "unauthorized", "message": "ต้องเปิดจาก LINE หรือ LAN สำนักงานใหญ่"},
                status_code=err.status_code,
            )
        return None, err
    return ident, None


def _err(exc: Exception) -> JSONResponse:
    if isinstance(exc, OnlineSaleError):
        return JSONResponse(
            {"error": exc.code, "message": exc.message, "detail": exc.message},
            status_code=exc.status,
        )
    return JSONResponse(
        {"error": "server_error", "message": str(exc), "detail": str(exc)},
        status_code=500,
    )


@router.get("/")
def ui_home(request: Request):
    ident, err = _require(request)
    if err is not None:
        return err
    settings = _settings()
    resp = HTMLResponse(
        page(user_name=_actor(ident), write_enabled=settings.write_enabled)
    )
    _set_session(resp, ident)
    return resp


@router.get("/api/meta")
def api_meta(request: Request):
    _, err = _require_api(request)
    if err is not None:
        return err
    return meta_payload()


@router.get("/api/shops")
def api_shops(request: Request, platform: str = ""):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return shops_payload(platform)
    except Exception as exc:
        return _err(exc)


@router.get("/api/product")
def api_product(request: Request, code: str = ""):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return product_payload(code)
    except Exception as exc:
        return _err(exc)


@router.post("/api/check-po")
def api_check_po(request: Request, body: CheckPoBody):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return check_po_payload(body.acctno, body.online_po)
    except Exception as exc:
        return _err(exc)


@router.post("/api/sales")
def api_sales(request: Request, body: SaleBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return save_sale_payload(body.model_dump(), _actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/api/search")
def api_search(
    request: Request,
    q: str = "",
    platform: str = "",
    acctno: str = "",
    date_from: str = "",
    date_to: str = "",
):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return search_payload(
            q=q,
            platform=platform,
            acctno=acctno,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        return _err(exc)


@router.get("/api/bills/{billno}")
def api_bill(request: Request, billno: str):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return bill_payload(billno)
    except Exception as exc:
        return _err(exc)


@router.get("/api/returns/preview")
def api_return_preview(request: Request, tad: str = ""):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return return_preview_payload(tad)
    except Exception as exc:
        return _err(exc)


@router.post("/api/returns")
def api_returns(request: Request, body: ReturnBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return save_return_payload(body.model_dump(), _actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/print/tad/{billno}", response_class=HTMLResponse)
def print_tad(request: Request, billno: str):
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(print_tad_html(billno))
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)


@router.get("/print/cntad/{billno}", response_class=HTMLResponse)
def print_cntad(request: Request, billno: str, reason: str = ""):
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(print_cntad_html(billno, reason=reason))
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)
