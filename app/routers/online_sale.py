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
    cancel_draft_payload,
    check_po_payload,
    draft_payload,
    meta_payload,
    print_cntad_html,
    print_pick_html,
    print_tad_html,
    product_payload,
    return_preview_payload,
    save_draft_payload,
    save_return_payload,
    save_sale_payload,
    search_payload,
    shops_payload,
    update_sale_payload,
)
from src.online_sale.ui import APP, SESSION_COOKIE, page
from src.staff_shell.auth import STAFF_COOKIE, identity_from_staff_cookie_for_app
from src.staff_shell.wiring import entry_source, shell_page, stamp_staff_session, wire_shell
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import is_tailscale_cg_nat
from src.to_bill.ui import APP as TO_APP
from src.to_bill.ui import SESSION_COOKIE as TO_SESSION_COOKIE

router = APIRouter(prefix="/online-sale", tags=["kcw-online-sale"])


class SaleBody(BaseModel):
    acctno: str = ""
    online_po: str = ""
    platform: str = ""
    draft_id: str = ""
    allow_oversell: bool = False
    confirm_unmapped: bool = False
    lines: list[dict[str, Any]] = Field(default_factory=list)


class CheckPoBody(BaseModel):
    acctno: str = ""
    online_po: str = ""
    platform: str = ""
    exclude_billno: str = ""
    exclude_draft_id: str = ""


class ReturnBody(BaseModel):
    tad_billno: str = ""
    reason_id: str = ""
    reason_note: str = ""
    confirm_unmapped: bool = False
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
    settings = _settings()
    staff = identity_from_staff_cookie_for_app(
        request.cookies,
        secret=settings.token_secret,
        app=APP,
        expected_branch="HQ",
    )
    if staff is not None:
        return staff
    ip = _client_ip(request)
    if is_tailscale_cg_nat(ip):
        return _named("tailscale", "tailnet")
    if is_private_lan(ip):
        return _named("lan", "LAN")
    return None



def _set_session(resp, identity, *, request: Request | None = None, has_entry_token: bool = False) -> None:
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
    had_staff = bool(request and request.cookies.get(STAFF_COOKIE)) if request else False
    source, log_open = entry_source(had_staff_cookie=had_staff, has_entry_token=has_entry_token)
    stamp_staff_session(
        resp,
        identity,
        secret=settings.token_secret,
        ttl_seconds=ttl,
        service_id="online-sale",
        source=source,
        path="/online-sale/",
        log_open=log_open,
    )


def _shell_identity(request: Request):
    return _identity_from_request(request)


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
    has_t = bool((request.query_params.get("t") or "").strip())
    ttl = max(settings.stock_check_token_ttl_seconds, 86400)
    # Mint a to-bill entry token for the iframe so it never races into LAN identity.
    to_bill_token = mint_access_token(
        secret=settings.token_secret,
        line_user_id=ident.line_user_id,
        display_name=ident.display_name,
        branch=ident.branch,
        ttl_seconds=ttl,
        app=TO_APP,
    )
    resp = HTMLResponse(
        shell_page(
            page(
                user_name=_actor(ident),
                write_enabled=settings.write_enabled,
                to_bill_token=to_bill_token,
            ),
            service_id="online-sale",
            api_base="/online-sale/_shell",
            user_name=_actor(ident),
            branch="HQ",
        )
    )
    _set_session(resp, ident, request=request, has_entry_token=has_t)
    return resp


wire_shell(
    router,
    current_service_id="online-sale",
    session_cookie=SESSION_COOKIE,
    session_cookie_path="/online-sale",
    get_secret=lambda: _settings().token_secret,
    get_ttl=lambda: max(_settings().stock_check_token_ttl_seconds, 86400),
    get_site=lambda: "HQ",
    get_app_identity=_shell_identity,
)


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
        return check_po_payload(
            body.acctno,
            body.online_po,
            platform=body.platform,
            exclude_billno=body.exclude_billno,
            exclude_draft_id=body.exclude_draft_id,
        )
    except Exception as exc:
        return _err(exc)


@router.post("/api/drafts")
def api_save_draft(request: Request, body: SaleBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return save_draft_payload(body.model_dump(), _actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/api/drafts/{draft_id}")
def api_get_draft(request: Request, draft_id: str):
    _, err = _require_api(request)
    if err is not None:
        return err
    try:
        return draft_payload(draft_id)
    except Exception as exc:
        return _err(exc)


@router.delete("/api/drafts/{draft_id}")
def api_cancel_draft(request: Request, draft_id: str):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return cancel_draft_payload(draft_id, _actor(ident))
    except Exception as exc:
        return _err(exc)


@router.post("/api/sales")
def api_sales(request: Request, body: SaleBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        data = body.model_dump()
        confirm = bool(data.pop("confirm_unmapped", False))
        return save_sale_payload(
            data,
            _actor(ident),
            line_user_id=ident.line_user_id,
            confirm_unmapped=confirm,
        )
    except Exception as exc:
        return _err(exc)


@router.patch("/api/sales/{billno}")
def api_update_sale(request: Request, billno: str, body: SaleBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return update_sale_payload(billno, body.model_dump(), _actor(ident))
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
    kind: str = "",
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
            kind=kind,
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
        data = body.model_dump()
        confirm = bool(data.pop("confirm_unmapped", False))
        return save_return_payload(
            data,
            _actor(ident),
            line_user_id=ident.line_user_id,
            confirm_unmapped=confirm,
        )
    except Exception as exc:
        return _err(exc)


def _embed_print_html(html: str, *, embed: bool) -> str:
    """VAT register embeds the live online-sale sheet; skip auto-print there."""
    if not embed:
        return html
    return html.replace("window.print();", "").replace(
        "setTimeout(function(){ window.print(); }, 200);",
        "",
    )


@router.get("/print/tad/{billno}", response_class=HTMLResponse)
def print_tad(request: Request, billno: str, embed: int = 0):
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(_embed_print_html(print_tad_html(billno), embed=bool(embed)))
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)


@router.get("/print/pick", response_class=HTMLResponse)
def print_pick_multi(request: Request, drafts: str = "", bills: str = ""):
    """Pick sheet from drafts (order ids). Legacy `bills` query is treated as draft ids."""
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(print_pick_html(draft_ids=[drafts or bills]))
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)


@router.get("/print/pick/{draft_id}", response_class=HTMLResponse)
def print_pick(request: Request, draft_id: str):
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(print_pick_html(draft_ids=[draft_id]))
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)


@router.get("/print/cntad/{billno}", response_class=HTMLResponse)
def print_cntad(request: Request, billno: str, reason: str = "", embed: int = 0):
    _, err = _require(request)
    if err is not None:
        return err
    try:
        return HTMLResponse(
            _embed_print_html(print_cntad_html(billno, reason=reason), embed=bool(embed))
        )
    except Exception as exc:
        if isinstance(exc, OnlineSaleError):
            return HTMLResponse(f"<h1>{exc.message}</h1>", status_code=exc.status)
        return HTMLResponse(f"<h1>{exc}</h1>", status_code=500)
