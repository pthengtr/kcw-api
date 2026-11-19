from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.receive_notes.company_banks import (
    DEFAULT_RECEIVE_BANK_KEY,
    list_company_receive_accounts,
)
from src.receive_notes.config import get_receive_notes_settings
from src.receive_notes.db import (
    daily_channel_totals,
    get_receipt,
    get_receive_notes_supabase_client,
    list_notes,
    list_receipts,
    list_review_queue,
    patch_receipt,
)
from src.receive_notes.net import is_tailscale_cg_nat
from src.receive_notes.parts9 import (
    debtor_summary,
    get_note_header,
    list_brdet,
    list_note_bills,
    list_pending_notes,
    list_pickable_bills,
    list_vouchered,
    search_debtors,
)
from src.receive_notes.service import (
    ReceiveServiceError,
    complete_tiger_receipt,
    create_note,
    prepare_receive,
    resync_receipt,
)
from src.receive_notes.storage import (
    list_folder,
    payment_image_prefix,
    public_url,
    receipt_image_prefix,
    safe_storage_filename,
    upload_bytes,
)
from src.receive_notes.tiger import get_ar_attempt, list_ar_attempts_for_day
from src.receive_notes.ui import APP, SESSION_COOKIE, page
from src.receive_notes.writer import ReceiveNoteWriteError
from src.staff_shell.auth import STAFF_COOKIE, identity_from_staff_cookie_for_app
from src.staff_shell.wiring import entry_source, shell_page, stamp_staff_session, wire_shell
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token

router = APIRouter(prefix="/receive-notes", tags=["receive-notes"])


def _settings():
    return get_receive_notes_settings()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return ""


def _verify_token(token: str):
    settings = _settings()
    try:
        return verify_access_token(
            token,
            secret=settings.token_secret,
            expected_branch=settings.site,
            expected_app=APP,
        )
    except TokenError:
        other = "SYP" if settings.site.upper() != "SYP" else "HQ"
        return verify_access_token(
            token,
            secret=settings.token_secret,
            expected_branch=other,
            expected_app=APP,
        )


def _identity_from_request(request: Request):
    token = request.cookies.get(SESSION_COOKIE) or request.query_params.get("t")
    if token:
        try:
            return _verify_token(token)
        except TokenError:
            pass
    settings = _settings()
    staff = identity_from_staff_cookie_for_app(
        request.cookies,
        secret=settings.token_secret,
        app=APP,
        expected_branch=settings.site,
    )
    if staff is not None:
        return staff
    if is_tailscale_cg_nat(_client_ip(request)):
        return None
    return False



def _tailscale_identity():
    from src.stock_check.auth import StockCheckIdentity

    settings = _settings()
    return StockCheckIdentity(
        line_user_id="tailscale",
        display_name="tailnet",
        branch=settings.site,
        app=APP,
    )


def _set_session(resp, identity, *, request: Request | None = None, has_entry_token: bool = False) -> None:
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
        max_age=86400 * 7,
        path="/receive-notes",
    )
    had_staff = bool(request and request.cookies.get(STAFF_COOKIE)) if request else False
    source, log_open = entry_source(had_staff_cookie=had_staff, has_entry_token=has_entry_token)
    stamp_staff_session(
        resp,
        identity,
        secret=settings.token_secret,
        ttl_seconds=ttl,
        service_id="receive-notes",
        source=source,
        path="/receive-notes/",
        log_open=log_open,
    )


def _shell_identity(request: Request):
    ident = _identity_from_request(request)
    if ident is False:
        return None
    if ident is None:
        return _tailscale_identity()
    return ident


def _require_identity(request: Request):
    return _shell_identity(request)


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    code = getattr(exc, "code", "error")
    return JSONResponse({"ok": False, "error": str(exc), "code": code}, status_code=status)


class NoteCreateBody(BaseModel):
    acctno: str
    acctname: str = ""
    billnos: list[str] = Field(default_factory=list)
    due_date: str | None = None
    remark: str | None = None


class ChannelBody(BaseModel):
    settle_method: str
    amount: float
    chkno: str | None = None
    chkdate: str | None = None
    receive_bank_key: str | None = None
    bankname: str | None = None


class AllocBody(BaseModel):
    billno: str
    allocate_amt: float | None = None


class ReceiveBody(BaseModel):
    acctno: str
    acctname: str = ""
    allocations: list[AllocBody]
    channels: list[ChannelBody]
    discount: float = 0.0
    noteno: str | None = None
    remark: str | None = None
    money_confirmed: bool = False
    cash_mode: str | None = "tiger"
    cash_manual_reason: str | None = None


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    settings = _settings()
    if not settings.receive_notes_enabled:
        return HTMLResponse("receive-notes disabled", status_code=503)
    ident = _identity_from_request(request)
    has_token = bool(request.query_params.get("t"))
    if ident is False:
        return HTMLResponse("unauthorized — open from LINE or Tailscale", status_code=401)
    if ident is None:
        ident = _tailscale_identity()
    name = ident.display_name or ident.line_user_id
    html = shell_page(
        page(
            user_name=name,
            site=settings.site,
            write_enabled=settings.receive_notes_write_enabled,
        ),
        service_id="receive-notes",
        api_base="/receive-notes/_shell",
        user_name=name,
        branch=settings.site,
    )
    resp = HTMLResponse(html)
    if ident.line_user_id != "tailscale":
        _set_session(resp, ident, request=request, has_entry_token=has_token)
    return resp


wire_shell(
    router,
    current_service_id="receive-notes",
    session_cookie=SESSION_COOKIE,
    session_cookie_path="/receive-notes",
    get_secret=lambda: _settings().token_secret,
    get_ttl=lambda: max(_settings().stock_check_token_ttl_seconds, 86400),
    get_site=lambda: _settings().site,
    get_app_identity=_shell_identity,
)


@router.get("/api/health")
def api_health():
    settings = _settings()
    return {
        "ok": True,
        "service": "receive-notes",
        "site": settings.site,
        "write_enabled": settings.receive_notes_write_enabled,
    }


@router.get("/api/company-receive-accounts")
def api_company_banks(request: Request):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    return {
        "ok": True,
        "accounts": list_company_receive_accounts(),
        "default": DEFAULT_RECEIVE_BANK_KEY,
    }


@router.get("/api/debtors")
def api_debtors(request: Request, q: str = ""):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    settings = _settings()
    try:
        rows = search_debtors(settings.site, q)
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "debtors": rows}


@router.get("/api/bills")
def api_bills(request: Request, acctno: str = ""):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    settings = _settings()
    try:
        rows = list_pickable_bills(settings.site, acctno)
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "bills": rows}


@router.get("/api/debtor-summary")
def api_debtor_summary(request: Request, acctno: str = ""):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    settings = _settings()
    try:
        data = debtor_summary(settings.site, acctno)
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, **data}


@router.get("/api/pending-notes")
def api_pending_notes(request: Request):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    settings = _settings()
    try:
        rows = list_pending_notes(settings.site)
        overlay = {f"{n['acctno']}|{n['noteno']}": n for n in list_notes(get_receive_notes_supabase_client())}
        for row in rows:
            key = f"{row['acctno']}|{row['noteno']}"
            row["overlay"] = overlay.get(key)
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "notes": rows}


@router.get("/api/notes/detail")
def api_note_detail(request: Request, acctno: str = "", noteno: str = ""):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    settings = _settings()
    try:
        header = get_note_header(settings.site, acctno, noteno)
        bills = list_note_bills(settings.site, acctno, noteno)
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "header": header, "bills": bills}


@router.post("/api/notes")
def api_create_note(request: Request, body: NoteCreateBody):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        result = create_note(
            acctno=body.acctno,
            acctname=body.acctname,
            billnos=body.billnos,
            due_date=body.due_date,
            remark=body.remark,
            operator=ident.display_name or ident.line_user_id,
        )
    except (ReceiveNoteWriteError, ReceiveServiceError) as exc:
        return _err(exc)
    return {"ok": True, **result}


@router.post("/api/receive")
def api_receive(request: Request, body: ReceiveBody):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        result = prepare_receive(
            acctno=body.acctno,
            acctname=body.acctname,
            allocations=[a.model_dump() for a in body.allocations],
            channels=[c.model_dump() for c in body.channels],
            discount=body.discount,
            noteno=body.noteno,
            remark=body.remark,
            money_confirmed=body.money_confirmed,
            cash_mode=body.cash_mode,
            cash_manual_reason=body.cash_manual_reason,
            operator=ident.display_name or ident.line_user_id,
        )
    except (ReceiveServiceError, ReceiveNoteWriteError, ValueError) as exc:
        return _err(exc)
    return {"ok": True, **result}


@router.get("/api/review")
def api_review(request: Request):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        rows = list_review_queue(get_receive_notes_supabase_client())
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "items": rows}


@router.get("/api/receipts")
def api_receipts(
    request: Request,
    received_at: str | None = None,
    acctno: str | None = None,
    workflow_status: str | None = None,
):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        rows = list_receipts(
            get_receive_notes_supabase_client(),
            received_at=received_at,
            acctno=acctno,
            workflow_status=workflow_status,
        )
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "receipts": rows}


@router.get("/api/receipts/{receipt_id}")
def api_receipt_detail(request: Request, receipt_id: str):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    row = get_receipt(get_receive_notes_supabase_client(), receipt_id)
    if not row:
        return _err(ReceiveServiceError("not found", code="not_found"), 404)
    settings = _settings()
    brdet = list_brdet(settings.site, row.get("voucno") or "") if row.get("voucno") else []
    tiger = get_ar_attempt(receipt_id)
    return {"ok": True, "receipt": row, "brdet": brdet, "tiger": tiger}


@router.get("/api/receipts/{receipt_id}/tiger")
def api_receipt_tiger(request: Request, receipt_id: str):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    return {"ok": True, "attempt": get_ar_attempt(receipt_id)}


@router.post("/api/receipts/{receipt_id}/complete-tiger")
def api_complete_tiger(request: Request, receipt_id: str):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        result = complete_tiger_receipt(
            receipt_id=receipt_id,
            operator=ident.display_name or ident.line_user_id,
        )
    except ReceiveServiceError as exc:
        return _err(exc)
    return {"ok": True, **result}


@router.post("/api/receipts/{receipt_id}/resync")
def api_resync(request: Request, receipt_id: str):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    try:
        result = resync_receipt(
            receipt_id=receipt_id,
            operator=ident.display_name or ident.line_user_id,
        )
    except ReceiveServiceError as exc:
        return _err(exc)
    return {"ok": True, **result}


@router.post("/api/receipts/{receipt_id}/confirm-money")
def api_confirm_money(request: Request, receipt_id: str):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        return _err(ReceiveServiceError("not found", code="not_found"), 404)
    patch_receipt(client, receipt_id, {"money_confirmed": True, "proof_status": "awaiting", "workflow_status": "awaiting_proof"})
    try:
        result = resync_receipt(
            receipt_id=receipt_id,
            operator=ident.display_name or ident.line_user_id,
        )
    except ReceiveServiceError as exc:
        return _err(exc)
    return {"ok": True, **result}


@router.post("/api/images/payment")
async def api_upload_payment(
    request: Request,
    voucno: str = Form(""),
    receipt_id: str = Form(""),
    file: UploadFile = File(...),
):
    ident = _require_identity(request)
    if not ident:
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    client = get_receive_notes_supabase_client()
    data = await file.read()
    name = safe_storage_filename(file.filename)
    if voucno.strip():
        prefix = payment_image_prefix(voucno.strip())
    elif receipt_id.strip():
        prefix = receipt_image_prefix(receipt_id.strip())
    else:
        return _err(ReceiveServiceError("voucno or receipt_id required", code="validation"))
    path = f"{prefix}/{name}"
    upload_bytes(client, path=path, data=data, content_type=file.content_type)
    if receipt_id.strip():
        patch_receipt(
            client,
            receipt_id.strip(),
            {"proof_status": "attached", "workflow_status": "done"},
        )
    elif voucno.strip():
        # match by voucno
        from src.receive_notes.db import get_receipt_by_voucno

        row = get_receipt_by_voucno(client, voucno.strip())
        if row:
            patch_receipt(client, row["id"], {"proof_status": "attached", "workflow_status": "done"})
    return {"ok": True, "path": path, "url": public_url(path)}


@router.get("/api/images/payment")
def api_list_payment_images(request: Request, voucno: str = "", receipt_id: str = ""):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    client = get_receive_notes_supabase_client()
    if voucno.strip():
        prefix = payment_image_prefix(voucno.strip())
    elif receipt_id.strip():
        prefix = receipt_image_prefix(receipt_id.strip())
    else:
        return _err(ReceiveServiceError("voucno or receipt_id required", code="validation"))
    items = list_folder(client, prefix)
    for item in items:
        item["url"] = public_url(item.get("path") or "")
    return {"ok": True, "images": items}


@router.get("/api/reports/daily")
def api_daily_report(request: Request, received_at: str | None = None):
    if not _require_identity(request):
        return _err(ReceiveServiceError("unauthorized", code="unauthorized"), 401)
    day = (received_at or date.today().isoformat()).strip()
    client = get_receive_notes_supabase_client()
    try:
        totals = daily_channel_totals(client, day)
        tiger = list_ar_attempts_for_day(day)
        kss = [
            v
            for v in list_vouchered(_settings().site, limit=300, days=3)
            if str(v.get("VOUCDATE") or v.get("voucdate") or "")[:10] == day
        ]
    except Exception as exc:
        return _err(exc, 500)
    return {"ok": True, "totals": totals, "tiger_attempts": tiger, "kss_vouchers": kss}
