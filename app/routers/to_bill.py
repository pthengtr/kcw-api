from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import is_tailscale_cg_nat
from src.to_bill.config import get_to_bill_settings
from src.to_bill.errors import ToBillError
from src.to_bill.net import is_private_lan
from src.to_bill.service import (
    buyers,
    get_one,
    issue,
    month_list,
    next_number,
    open_draft,
    printed,
    refresh,
    save,
    search,
    void,
)
from src.to_bill.ui import APP, SESSION_COOKIE, page

router = APIRouter(prefix="/to-bill", tags=["kcw-to-bill"])


class DraftBody(BaseModel):
    tad_billno: str = ""


class BuyerBody(BaseModel):
    customer_name: str = ""
    address: str = ""
    phone: str = ""
    tax_id: str = ""
    branch_label: str = ""
    branch_no: str = ""
    email: str = ""


class VoidBody(BaseModel):
    reason: str = ""


def _settings():
    return get_to_bill_settings()


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
        path="/to-bill",
    )


def _actor(identity) -> str:
    name = (identity.display_name or identity.line_user_id or "").strip()
    return name[:80] or "unknown"


def _require(request: Request):
    settings = _settings()
    if not settings.to_bill_enabled:
        return None, HTMLResponse("to bill disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is None:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ ใบเต็มออนไลน์ ในแชท หรือเปิดจากเครือข่ายสำนักงาน</p>",
            status_code=401,
        )
    return ident, None


def _require_api(request: Request):
    ident, err = _require(request)
    if err:
        return None, JSONResponse({"error": "unauthorized"}, status_code=401)
    return ident, None


def _error(exc: ToBillError):
    return JSONResponse(
        {"error": exc.code, "message": str(exc)},
        status_code=exc.status,
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None, tad: str | None = None):
    ident, err = _require(request)
    if err and t:
        try:
            ident = _verify_token(t)
            err = None
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
    if err:
        return err
    if t:
        dest = "/to-bill/"
        if tad:
            dest += f"?tad={tad}"
        resp = RedirectResponse(url=dest, status_code=303)
        _set_session(resp, ident)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    resp = HTMLResponse(page(user_name=ident.display_name))
    resp.headers["Cache-Control"] = "no-store"
    _set_session(resp, ident)
    return resp


@router.get("/new")
def new_from_link(tad: str = ""):
    dest = "/to-bill/"
    if tad.strip():
        dest += f"?tad={tad.strip()}"
    return RedirectResponse(url=dest, status_code=307)


@router.get("/api/search")
def api_search(request: Request, q: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return search(q)
    except ToBillError as exc:
        return _error(exc)


@router.get("/api/invoices")
def api_list(request: Request, status: str = "", q: str = "", yymm: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return month_list(status=status, q=q, yymm=yymm)
    except ToBillError as exc:
        return _error(exc)


@router.get("/api/next-number")
def api_next(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return next_number()
    except ToBillError as exc:
        return _error(exc)


@router.get("/api/buyers")
def api_buyers(request: Request, q: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return buyers(q)
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/drafts")
def api_draft(request: Request, body: DraftBody):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        return open_draft(body.tad_billno, _actor(ident))
    except ToBillError as exc:
        return _error(exc)


@router.get("/api/invoices/{invoice_id}")
def api_get(request: Request, invoice_id: str):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return get_one(invoice_id)
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/invoices/{invoice_id}/refresh")
def api_refresh(request: Request, invoice_id: str):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        return refresh(invoice_id, _actor(ident))
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/invoices/{invoice_id}/buyer")
def api_buyer(request: Request, invoice_id: str, body: BuyerBody):
    _, err = _require_api(request)
    if err:
        return err
    try:
        return save(invoice_id, body.model_dump())
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/invoices/{invoice_id}/issue")
def api_issue(request: Request, invoice_id: str, body: BuyerBody):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        return issue(invoice_id, body.model_dump(), _actor(ident))
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/invoices/{invoice_id}/void")
def api_void(request: Request, invoice_id: str, body: VoidBody):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        return void(invoice_id, body.reason, _actor(ident))
    except ToBillError as exc:
        return _error(exc)


@router.post("/api/invoices/{invoice_id}/printed")
def api_printed(request: Request, invoice_id: str):
    ident, err = _require_api(request)
    if err:
        return err
    try:
        printed(invoice_id, _actor(ident))
    except ToBillError as exc:
        return _error(exc)
    return {"ok": True}
