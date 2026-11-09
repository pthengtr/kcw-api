from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.net import is_private_lan
from src.hq_receive.service import (
    confirm_receipt,
    create_draft,
    create_product_payload,
    credit_notes_payload,
    discrepancies_payload,
    extract_invoice,
    fill_vendor_credit_note,
    get_draft,
    history_payload,
    match_invoice,
    meta_payload,
    open_lines_payload,
    open_pos_payload,
    open_vendors_payload,
    save_draft,
    sticker_config,
    sticker_jobs,
    sticker_preview,
    sticker_print,
    vendors_payload,
)
from src.hq_receive.ui import APP, SESSION_COOKIE, page
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.stock_check.net import is_tailscale_cg_nat

router = APIRouter(prefix="/hq-receive", tags=["kcw-hq-receive"])


class ReceiptBody(BaseModel):
    vendor_acctno: str = ""
    vendor_name: str | None = None
    vendor_billno: str = ""
    vendor_bill_date: str | None = None
    receive_date: str | None = None
    pay_method: str = "credit"
    receiver: str = ""
    discount: float = 0
    tax: float = 0
    vat_rate: int | float | None = None
    net: float = 0
    notes: str | None = None
    extraction_id: str | None = None
    po_docnos: list[str] = Field(default_factory=list)
    lines: list[dict[str, Any]] = Field(default_factory=list)


class MatchBody(BaseModel):
    vendor_acctno: str = ""


class StickerLine(BaseModel):
    bcode: str = ""
    qty: float = 1
    descr: str = ""


class StickerBody(BaseModel):
    lines: list[dict[str, Any]] = Field(default_factory=list)
    printer_model: str = ""
    printer_host: str = ""
    action: str = "download"
    receipt_id: str | None = None
    pimas_billno: str | None = None
    all_previews: bool = False


class VendorCnBody(BaseModel):
    vendor_cn_no: str = ""
    vendor_cn_date: str | None = None


class ProductBody(BaseModel):
    bcode: str = ""
    descr: str = ""
    ui: str = "ชิ้น"
    vendor: str = ""
    vendor_acctno: str = ""
    brand: str = ""
    model: str = ""
    pcode: str = ""
    mcode: str = ""
    cost: float = 0
    qtymin: float = 0
    main: int | None = None


def _settings():
    return get_hq_receive_settings()


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
        path="/hq-receive",
    )


def _actor(identity) -> str:
    name = (identity.display_name or identity.line_user_id or "").strip()
    return name[:80] or "unknown"


def _require(request: Request):
    settings = _settings()
    if not settings.hq_receive_enabled:
        return None, HTMLResponse("hq receive disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is None:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ รับสินค้า ในแชท หรือเปิดจากเครือข่ายสำนักงานใหญ่</p>",
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
    if isinstance(exc, HqReceiveError):
        return JSONResponse(
            {"error": exc.code, "message": exc.message, "detail": exc.message},
            status_code=400,
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
    ident, err = _require_api(request)
    if err is not None:
        return err
    return meta_payload()


@router.get("/api/vendors")
def api_vendors(request: Request, q: str = ""):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        if (q or "").strip():
            return vendors_payload(q=q)
        return open_vendors_payload()
    except Exception as exc:
        return _err(exc)


@router.get("/api/open-pos")
def api_open_pos(request: Request, acctno: str = ""):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return open_pos_payload(acctno=acctno)
    except Exception as exc:
        return _err(exc)


@router.get("/api/open-lines")
def api_open_lines(request: Request, acctno: str = "", q: str = "", po: str = ""):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        po_docnos = [p.strip() for p in (po or "").split(",") if p.strip()]
        return open_lines_payload(acctno=acctno, q=q, po_docnos=po_docnos or None)
    except Exception as exc:
        return _err(exc)


@router.post("/api/products")
def api_create_product(request: Request, body: ProductBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return create_product_payload(body.model_dump(), actor=_actor(ident))
    except Exception as exc:
        return _err(exc)


@router.post("/api/invoices/extract")
async def api_invoice_extract(
    request: Request,
    file: UploadFile = File(...),
    vendor_acctno: str = Form(""),
):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        raw = await file.read()
        return extract_invoice(
            image_bytes=raw,
            content_type=file.content_type,
            vendor_acctno=vendor_acctno,
            file_name=file.filename or "",
            actor=_actor(ident),
        )
    except Exception as exc:
        return _err(exc)


@router.post("/api/invoices/{extraction_id}/match")
def api_invoice_match(request: Request, extraction_id: str, body: MatchBody | None = None):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        vendor = (body.vendor_acctno if body else "") or ""
        return match_invoice(extraction_id, vendor_acctno=vendor, actor=_actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/api/discrepancies")
def api_discrepancies(request: Request, status: str = "open", limit: int = 80):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return discrepancies_payload(status=status, limit=max(1, min(int(limit or 80), 200)))
    except Exception as exc:
        return _err(exc)


@router.get("/api/credit-notes")
def api_credit_notes(request: Request, status: str = "", limit: int = 80):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return credit_notes_payload(
            status=status, limit=max(1, min(int(limit or 80), 200))
        )
    except Exception as exc:
        return _err(exc)


@router.post("/api/credit-notes/{credit_note_id}/vendor-doc")
def api_credit_note_vendor_doc(
    request: Request, credit_note_id: str, body: VendorCnBody
):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return fill_vendor_credit_note(
            credit_note_id,
            vendor_cn_no=body.vendor_cn_no,
            vendor_cn_date=body.vendor_cn_date,
            actor=_actor(ident),
        )
    except Exception as exc:
        return _err(exc)


@router.post("/api/receipts")
def api_create_receipt(request: Request, body: ReceiptBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return create_draft(body.model_dump(), actor=_actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/api/receipts/{receipt_id}")
def api_get_receipt(request: Request, receipt_id: str):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return get_draft(receipt_id)
    except Exception as exc:
        return _err(exc)


@router.put("/api/receipts/{receipt_id}")
def api_put_receipt(request: Request, receipt_id: str, body: ReceiptBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return save_draft(receipt_id, body.model_dump(), actor=_actor(ident))
    except Exception as exc:
        return _err(exc)


@router.post("/api/receipts/{receipt_id}/confirm")
def api_confirm(request: Request, receipt_id: str):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return confirm_receipt(receipt_id, actor=_actor(ident))
    except Exception as exc:
        return _err(exc)


@router.get("/api/history")
@router.get("/api/receipts/history")
def api_history(request: Request, limit: int = 40):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return history_payload(limit=max(1, min(int(limit or 40), 100)))
    except Exception as exc:
        return _err(exc)


@router.get("/api/stickers/config")
def api_sticker_config(request: Request):
    ident, err = _require_api(request)
    if err is not None:
        return err
    return sticker_config()


@router.post("/api/stickers/preview")
def api_sticker_preview(request: Request, body: StickerBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return sticker_preview(body.model_dump())
    except Exception as exc:
        return _err(exc)


@router.post("/api/stickers/print")
def api_sticker_print(request: Request, body: StickerBody):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        result = sticker_print(body.model_dump(), actor=_actor(ident))
        if result.get("download") and result.get("prn_b64"):
            raw = base64.standard_b64decode(result["prn_b64"])
            filename = result.get("filename") or "kcw-hq-receive-stickers.prn"
            return Response(
                content=raw,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return result
    except Exception as exc:
        return _err(exc)


@router.get("/api/stickers/jobs")
def api_sticker_jobs(request: Request, receipt_id: str = "", limit: int = 40):
    ident, err = _require_api(request)
    if err is not None:
        return err
    try:
        return sticker_jobs(receipt_id=receipt_id or None, limit=max(1, min(int(limit or 40), 100)))
    except Exception as exc:
        return _err(exc)


@router.get("", include_in_schema=False)
def ui_redirect():
    return RedirectResponse(url="/hq-receive/", status_code=307)
