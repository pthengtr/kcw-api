from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.pay_notes.config import get_pay_notes_settings
from src.pay_notes.db import (
    get_pay_notes_supabase_client,
    get_reminder,
    get_vendor_bank,
    insert_reminder,
    insert_vendor_bank,
    list_reminders,
    list_vendor_banks,
    patch_reminder,
)
from src.pay_notes.net import is_tailscale_cg_nat
from src.pay_notes.parts9 import (
    get_note_header,
    list_pending_notes,
    list_pickable_bills,
    list_vouchered_notes,
    note_exists,
    search_vendors,
)
from src.pay_notes.storage import (
    bill_image_prefix,
    list_folder,
    payment_image_prefix,
    public_url,
    upload_bytes,
)
from src.pay_notes.ui import APP, SESSION_COOKIE, page
from src.pay_notes.writer import PayNoteWriteError, cancel_unvouchered_pay_note, create_pay_note, create_voucher
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token

router = APIRouter(prefix="/pay-notes", tags=["pay-notes"])
_BKK = ZoneInfo("Asia/Bangkok")


def _settings():
    return get_pay_notes_settings()


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


def _set_session(resp, identity) -> None:
    settings = _settings()
    token = mint_access_token(
        secret=settings.token_secret,
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        app=APP,
    )
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        path="/pay-notes",
    )


def _require(request: Request):
    settings = _settings()
    if not settings.pay_notes_enabled:
        return None, HTMLResponse("pay-notes disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ ชำระเจ้าหนี้ ในแชท</p>",
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


class BankCreate(BaseModel):
    acctno: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    bank_branch: str | None = None
    account_type: str = "OTHER"
    is_default: bool = False


class NoteCreate(BaseModel):
    acctno: str
    acctname: str
    noteno: str
    due_date: str
    bank_id: str
    billnos: list[str] = Field(default_factory=list)
    discount_mode: str = "amount"  # amount | percent
    discount_input: float = 0.0


class ReminderPatch(BaseModel):
    due_date: str | None = None
    bank_id: str | None = None


class VoucherCreate(BaseModel):
    acctno: str
    noteno: str
    # transfer | cheque | cash — drives CHKNO defaults; discount stays on reminder
    settle_method: str = "transfer"
    chkno: str = ""
    chkamt: float
    chkdate: str | None = None
    bank_gl: str = "2101.7"


def _parse_due(raw: str) -> str:
    """Calendar due date as YYYY-MM-DD (no timezone)."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("due_date required")
    # Accept ISO datetime from old clients; use the calendar date the user picked.
    if "T" in text:
        text = text.split("T", 1)[0]
    return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()


def _resolve_discount(billamt: float, mode: str, raw_input: float) -> tuple[str, float, float]:
    m = (mode or "amount").strip().lower()
    if m not in ("amount", "percent"):
        m = "amount"
    val = float(raw_input or 0)
    if val < 0:
        raise ValueError("discount cannot be negative")
    bill = float(billamt or 0)
    if m == "percent":
        if val > 100:
            raise ValueError("discount percent cannot exceed 100")
        amount = round(bill * val / 100.0, 2)
    else:
        amount = round(val, 2)
    if amount - bill > 1e-9:
        raise ValueError("discount exceeds bill total")
    return m, val, amount


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    settings = _settings()
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
    name = ident.display_name if ident else "operator"
    html = page(user_name=name, site=settings.site, write_enabled=settings.pay_notes_write_enabled)
    resp = HTMLResponse(html)
    if ident and ident.line_user_id != "tailscale":
        _set_session(resp, ident)
    return resp


@router.get("/api/vendors")
def api_vendors(request: Request, q: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    try:
        rows = search_vendors(settings.site, q)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return rows


@router.get("/api/bills")
def api_bills(request: Request, acctno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    try:
        rows = list_pickable_bills(settings.site, acctno)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return rows


@router.get("/api/banks")
def api_banks(request: Request, acctno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    client = get_pay_notes_supabase_client()
    return list_vendor_banks(client, acctno)


@router.post("/api/banks")
def api_bank_create(request: Request, body: BankCreate):
    _, err = _require_api(request)
    if err:
        return err
    client = get_pay_notes_supabase_client()
    row = insert_vendor_bank(
        client,
        {
            "acctno": body.acctno.strip(),
            "bank_name": body.bank_name.strip(),
            "bank_account_name": body.bank_account_name.strip(),
            "bank_account_number": body.bank_account_number.strip(),
            "bank_branch": (body.bank_branch or "").strip() or None,
            "account_type": body.account_type.strip() or "OTHER",
            "is_default": body.is_default,
        },
    )
    return row


@router.get("/api/pending")
def api_pending(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    client = get_pay_notes_supabase_client()
    reminders = list_reminders(client)
    try:
        rows = list_pending_notes(settings.site, reminders)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return rows


@router.patch("/api/reminder/{acctno}/{noteno}")
def api_reminder_patch(request: Request, acctno: str, noteno: str, body: ReminderPatch):
    _, err = _require_api(request)
    if err:
        return err
    patch: dict[str, Any] = {"updated_at": datetime.now(_BKK).isoformat()}
    if body.due_date:
        patch["due_date"] = _parse_due(body.due_date)
    if body.bank_id:
        patch["bank_id"] = body.bank_id
    client = get_pay_notes_supabase_client()
    row = patch_reminder(client, acctno, noteno, patch)
    return row


@router.post("/api/images/bill")
async def api_upload_bill_image(
    request: Request,
    acctno: str = Form(...),
    noteno: str = Form(...),
    file: UploadFile = File(...),
):
    _, err = _require_api(request)
    if err:
        return err
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)
    acct = acctno.strip()
    note = noteno.strip()
    if not acct or not note:
        return JSONResponse({"error": "acctno and noteno required"}, status_code=400)
    prefix = bill_image_prefix(acct, note)
    name = (file.filename or "upload.jpg").replace("/", "_").replace("\\", "_")
    path = f"{prefix}/{name}"
    client = get_pay_notes_supabase_client()
    upload_bytes(client, path, data, content_type=file.content_type or "image/jpeg")
    return {"path": path, "url": public_url(path)}


@router.get("/api/images/bill")
def api_list_bill_images(request: Request, acctno: str = "", noteno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    client = get_pay_notes_supabase_client()
    return list_folder(client, bill_image_prefix(acctno, noteno))


@router.post("/api/notes")
def api_create_note(request: Request, body: NoteCreate):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = body.acctno.strip()
    note = body.noteno.strip()
    if len(note) > 15:
        return JSONResponse({"error": "NOTENO max 15 chars"}, status_code=400)
    if not body.billnos:
        return JSONResponse({"error": "select at least one bill"}, status_code=400)

    client = get_pay_notes_supabase_client()
    bank = get_vendor_bank(client, body.bank_id)
    if not bank or bank.get("acctno", "").strip() != acct:
        return JSONResponse({"error": "invalid bank for vendor"}, status_code=400)

    images = list_folder(client, bill_image_prefix(acct, note))
    if not images:
        return JSONResponse({"error": "upload at least one bill image first"}, status_code=400)

    # KSS + Supabase cannot share one ACID tx. Write KSS first, then reminder;
    # if reminder fails, compensate by canceling the unvouchered KSS note.
    recovered = False
    if note_exists(settings.site, acct, note):
        # Legacy orphan from before compensate: attach reminder only.
        if get_reminder(client, acct, note):
            return JSONResponse({"error": "note already exists in KSS"}, status_code=409)
        header = get_note_header(settings.site, acct, note)
        if not header:
            return JSONResponse({"error": "note already exists in KSS"}, status_code=409)
        kss = {
            "acctno": acct,
            "noteno": note,
            "billcnt": int(header.get("BILLCNT") or 0),
            "billamt": float(header.get("BILLAMT") or 0),
            "notedate": header.get("NOTEDATE"),
            "jourmode": str(header.get("JOURMODE") or "1").strip() or "1",
            "recovered": True,
        }
        recovered = True
    else:
        try:
            kss = create_pay_note(
                settings=settings,
                acctno=acct,
                acctname=body.acctname.strip(),
                noteno=note,
                billnos=body.billnos,
                operator=ident.display_name if ident else None,
            )
        except PayNoteWriteError as exc:
            return JSONResponse({"error": str(exc), "code": exc.code}, status_code=400)

    billamt = float(kss.get("billamt") or 0)
    try:
        discount_mode, discount_input, discount_amount = _resolve_discount(
            billamt, body.discount_mode, body.discount_input
        )
    except ValueError as exc:
        if not recovered:
            try:
                cancel_unvouchered_pay_note(settings=settings, acctno=acct, noteno=note)
            except Exception:
                pass
        return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)

    due = _parse_due(body.due_date)
    try:
        rem = insert_reminder(
            client,
            {
                "acctno": acct,
                "noteno": note,
                "due_date": due,
                "bank_id": body.bank_id,
                "discount_mode": discount_mode,
                "discount_input": discount_input,
                "discount_amount": discount_amount,
                "created_by": ident.line_user_id if ident else None,
            },
        )
    except Exception as exc:
        rolled_back = False
        rollback_error = None
        if not recovered:
            try:
                cancel_unvouchered_pay_note(settings=settings, acctno=acct, noteno=note)
                rolled_back = True
            except Exception as cancel_exc:
                rollback_error = str(cancel_exc)
        payload = {
            "error": f"reminder failed: {exc}",
            "code": "reminder_failed",
            "noteno": note,
            "kss_rolled_back": rolled_back,
        }
        if rollback_error:
            payload["kss_rollback_error"] = rollback_error
        return JSONResponse(payload, status_code=500)
    return {**kss, "reminder": rem}


@router.get("/api/notes/{acctno}/{noteno}")
def api_note_detail(request: Request, acctno: str, noteno: str):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    header = get_note_header(settings.site, acctno, noteno)
    if not header:
        return JSONResponse({"error": "not found"}, status_code=404)
    client = get_pay_notes_supabase_client()
    bills = list_folder(client, bill_image_prefix(acctno, noteno))
    proofs: list[dict[str, Any]] = []
    voucno = (header.get("voucno") or "").strip()
    if voucno:
        proofs = list_folder(client, payment_image_prefix(voucno))
    banks = list_vendor_banks(client, acctno)
    return {"header": header, "bill_images": bills, "payment_images": proofs, "banks": banks}


@router.post("/api/vouchers")
def api_create_voucher(request: Request, body: VoucherCreate):
    """Record voucher: discount from reminder; operator enters CHKNO/CHKAMT (settle method)."""
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = body.acctno.strip()
    note = body.noteno.strip()
    client = get_pay_notes_supabase_client()
    rem = get_reminder(client, acct, note)
    if not rem:
        return JSONResponse({"error": "reminder not found for this note"}, status_code=404)
    bank = get_vendor_bank(client, rem.get("bank_id") or "")
    if not bank:
        return JSONResponse({"error": "vendor bank missing on reminder"}, status_code=400)

    header = get_note_header(settings.site, acct, note)
    if not header:
        return JSONResponse({"error": "note not found in KSS"}, status_code=404)
    billamt = float(header.get("BILLAMT") or 0)
    disc = float(rem.get("discount_amount") or 0)
    if disc < 0 or disc - billamt > 1e-9:
        return JSONResponse({"error": "stored discount invalid"}, status_code=400)
    net = round(billamt - disc, 2)

    method = (body.settle_method or "transfer").strip().lower()
    if method not in ("transfer", "cheque", "cash"):
        method = "transfer"
    chkno = (body.chkno or "").strip()
    if method == "transfer" and not chkno:
        chkno = "โอน"
    if method == "cheque" and not chkno:
        return JSONResponse({"error": "cheque number (CHKNO) required"}, status_code=400)
    # cash: legacy often leaves CHKNO blank (or rare labels like จ่ายสด) — allow blank

    try:
        chkamt = float(body.chkamt)
    except (TypeError, ValueError):
        return JSONResponse({"error": "CHKAMT required"}, status_code=400)
    if chkamt <= 0 and net > 1e-9:
        return JSONResponse({"error": "CHKAMT must be > 0"}, status_code=400)
    if chkamt - net > 0.01:
        return JSONResponse(
            {"error": f"CHKAMT ({chkamt}) exceeds net payable ({net})"},
            status_code=400,
        )

    bankname = " ".join(
        p
        for p in (
            str(bank.get("bank_name") or "").strip(),
            str(bank.get("bank_account_name") or "").strip(),
            ("# " + str(bank.get("bank_account_number") or "").strip())
            if bank.get("bank_account_number")
            else "",
        )
        if p
    )[:60]
    if method == "cash":
        # Cash rows historically often have empty BANKNAME / GL
        bankname = ""
        bank_gl = (body.bank_gl or "").strip()[:10]
    else:
        bank_gl = (body.bank_gl or "2101.7").strip()[:10] or "2101.7"

    chkdate = (body.chkdate or "").strip() or datetime.now(_BKK).date().isoformat()
    bpdet_lines: list[dict[str, Any]] = []
    if chkamt > 1e-9:
        bpdet_lines = [
            {
                "chkno": chkno,  # may be blank for cash
                "chkamt": round(chkamt, 2),
                "bankname": bankname,
                "acctno": bank_gl,
                "paytype": 2,
                "chkdate": chkdate,
            }
        ]
    try:
        result = create_voucher(
            settings=settings,
            acctno=acct,
            noteno=note,
            discount=disc,
            bpdet_lines=bpdet_lines,
            operator=ident.display_name if ident else None,
        )
    except PayNoteWriteError as exc:
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=400)
    return {**result, "reminder": rem, "settle_method": method}


@router.get("/api/awaiting-proof")
def api_awaiting_proof(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    client = get_pay_notes_supabase_client()
    reminders = list_reminders(client)
    try:
        rows = list_vouchered_notes(settings.site, reminders)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    out = []
    for row in rows:
        voucno = (row.get("voucno") or "").strip()
        proofs = list_folder(client, payment_image_prefix(voucno)) if voucno else []
        if proofs:
            continue
        out.append({**row, "payment_images": proofs})
    return out


@router.post("/api/images/payment")
async def api_upload_payment_image(
    request: Request,
    voucno: str = Form(...),
    file: UploadFile = File(...),
):
    _, err = _require_api(request)
    if err:
        return err
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)
    vo = voucno.strip()
    if not vo:
        return JSONResponse({"error": "voucno required"}, status_code=400)
    prefix = payment_image_prefix(vo)
    name = (file.filename or "proof.jpg").replace("/", "_").replace("\\", "_")
    path = f"{prefix}/{name}"
    client = get_pay_notes_supabase_client()
    upload_bytes(client, path, data, content_type=file.content_type or "image/jpeg")
    return {"path": path, "url": public_url(path)}


@router.get("/api/images/payment")
def api_list_payment_images(request: Request, voucno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    client = get_pay_notes_supabase_client()
    return list_folder(client, payment_image_prefix(voucno))
