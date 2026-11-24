from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.pay_notes.baht_text import baht_text
from src.pay_notes.noteno import noteno_meta
from src.pay_notes.remark import resolve_remark_fields
from src.receive_notes.company_banks import (
    DEFAULT_RECEIVE_BANK_KEY,
    brdet_line_from_payment,
    list_company_receive_accounts,
    receive_bank_key_from_bankname,
    receive_bank_key_from_gl,
    resolve_company_receive_account,
    resolve_optional_receive_account,
)
from src.receive_notes.config import get_receive_notes_settings
from src.receive_notes.db import (
    NoteOverlayConflict,
    ensure_open_note,
    get_note,
    get_receipt_by_voucno,
    get_receive_notes_supabase_client,
    insert_note,
    list_all_service_notes,
    list_open_notes,
    list_receipt_edit_audits,
    patch_note,
)
from src.receive_notes.net import is_tailscale_cg_nat
from src.receive_notes.service import (
    ReceiveServiceError,
    edit_vouchered_receive_meta,
    note_refund_snapshot,
    start_note_cash_via_tiger,
    start_note_refund,
    sync_tiger_receipt,
    sync_tiger_refund,
)
from src.receive_notes.parts9 import (
    assess_receive_edit_gate,
    debtor_summary,
    get_debtor,
    get_note_header,
    infer_settle_method,
    list_bills_for_edit,
    list_brdet,
    list_canceled_notes,
    list_note_bills,
    list_pending_notes,
    list_pickable_bills,
    list_vouchered_notes,
    search_debtors,
)
from src.receive_notes.storage import (
    list_folder,
    payment_image_prefix,
    public_url,
    remove_paths,
    safe_storage_filename,
    upload_bytes,
)
from src.receive_notes.ui import APP, SESSION_COOKIE, page
from src.receive_notes.writer import (
    ReceiveNoteWriteError,
    cancel_unvouchered_receive_note,
    create_receipt_voucher,
    create_receive_note,
    proof_required,
    update_receive_note,
)
from src.staff_shell.auth import STAFF_COOKIE, identity_from_staff_cookie_for_app
from src.staff_shell.wiring import entry_source, shell_page, stamp_staff_session, wire_shell
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token

router = APIRouter(prefix="/receive-notes", tags=["receive-notes"])
_BKK = ZoneInfo("Asia/Bangkok")

NOTE_PAY_METHODS = ("transfer", "cheque")


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


def _require(request: Request):
    settings = _settings()
    if not settings.receive_notes_enabled:
        return None, HTMLResponse("receive-notes disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ รับชำระลูกหนี้ ในแชท</p>",
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


class NoteCreate(BaseModel):
    acctno: str
    acctname: str
    billnos: list[str] = Field(default_factory=list)
    discount_mode: str = "amount"  # amount | percent
    discount_input: float = 0.0
    remark: str = ""
    bill_month: str | None = None
    remark_extra: str | None = None
    settle_method: str | None = None  # legacy; ignored for new create UX
    receive_bank_key: str | None = None  # optional company bank on billing note
    due_date: str
    confirm_unmapped: bool = False


class NoteUpdate(BaseModel):
    billnos: list[str] = Field(default_factory=list)
    due_date: str | None = None
    remark: str | None = None
    bill_month: str | None = None
    remark_extra: str | None = None
    discount_mode: str | None = None
    discount_input: float | None = None
    settle_method: str | None = None  # legacy
    receive_bank_key: str | None = None


class ReminderPatch(BaseModel):
    due_date: str | None = None
    remark: str | None = None
    bill_month: str | None = None
    remark_extra: str | None = None
    discount_mode: str | None = None
    discount_input: float | None = None
    settle_method: str | None = None
    receive_bank_key: str | None = None


class VoucherCreate(BaseModel):
    acctno: str
    noteno: str
    # transfer | cheque | cash — drives CHKNO defaults; discount stays on overlay
    settle_method: str = "transfer"
    chkno: str = ""
    chkamt: float
    chkdate: str | None = None
    pay_bank: str = DEFAULT_RECEIVE_BANK_KEY
    receive_bank_key: str | None = None  # alias for pay_bank


class VoucherMetaEdit(BaseModel):
    """Post-voucher correction: receive date / remark / bank only."""

    acctno: str
    noteno: str
    received_at: str | None = None
    remark: str | None = None
    receive_bank_key: str | None = None
    accounting_reviewed: bool = False


def _parse_due(raw: str) -> str:
    """Calendar due date as YYYY-MM-DD (no timezone)."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("due_date required")
    if "T" in text:
        text = text.split("T", 1)[0]
    return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()


def _normalize_note_pay_method(raw: str | None, *, default: str = "transfer") -> str:
    """Legacy intended settlement on a billing note: transfer | cheque."""
    text = (raw if raw is not None else default) or default
    method = text.strip().lower()
    if method not in NOTE_PAY_METHODS:
        raise ValueError("settle_method must be transfer or cheque")
    return method


def _normalize_receive_bank_key(raw: str | None) -> str | None:
    """Optional company bank on billing note; empty clears."""
    text = (raw or "").strip()
    if not text:
        return None
    acct = resolve_optional_receive_account(text)
    if not acct:
        raise ValueError("unknown receive_bank_key")
    return acct["key"]


def _resolve_discount(billamt: float, mode: str, raw_input: float) -> tuple[str, float, float]:
    m = (mode or "amount").strip().lower()
    if m not in ("amount", "percent"):
        m = "amount"
    # Negative discount is allowed (acts as a surcharge, e.g. -0.01).
    val = float(raw_input or 0)
    bill = float(billamt or 0)
    if m == "percent":
        if val > 100:
            raise ValueError("discount percent cannot exceed 100")
        amount = round(bill * val / 100.0, 2)
    else:
        amount = round(val, 2)
    # Negative BILLAMT (ใบลดหนี้ / CN) is a valid BN/BNN total — not a discount.
    # Only reject when a discount exceeds a non-negative bill total.
    if bill >= 0 and amount - bill > 1e-9:
        raise ValueError("discount exceeds bill total")
    return m, val, amount


def _settle_method_of(row: dict[str, Any] | None = None, *, settle_method: str = "") -> str:
    if settle_method:
        return (settle_method or "").strip().lower()
    rem = (row or {}).get("reminder") or {}
    return str(
        (row or {}).get("settle_method")
        or rem.get("settle_method")
        or ""
    ).strip().lower()


def _proof_done(
    *,
    voucno: str = "",
    has_proof: bool = False,
    settle_method: str = "",
) -> bool:
    if has_proof:
        return True
    return not proof_required(voucno=voucno, settle_method=settle_method)


def _workflow_meta(
    *,
    voucno: str = "",
    has_proof: bool = False,
    canceled: bool = False,
    settle_method: str = "",
    is_refund: bool = False,
) -> dict[str, Any]:
    if canceled:
        return {
            "stage": "canceled",
            "workflow_status": "ยกเลิก",
            "is_editable": False,
            "canceled": True,
        }
    vo = (voucno or "").strip()
    if not vo:
        return {
            "stage": "pending",
            "workflow_status": "รอคืนเงิน" if is_refund else "รอรับชำระ",
            "is_editable": True,
            "canceled": False,
            "is_refund": bool(is_refund),
        }
    done = _proof_done(voucno=vo, has_proof=has_proof, settle_method=settle_method)
    needs_proof = proof_required(voucno=vo, settle_method=settle_method)
    is_pvn = vo.upper().startswith("PVN") or is_refund
    if not done:
        return {
            "stage": "await_proof",
            "workflow_status": "รอแนบหลักฐาน",
            "is_editable": False,
            "canceled": False,
            "proof_required": True,
            "is_refund": bool(is_pvn),
        }
    return {
        "stage": "voucher",
        "workflow_status": "ใบสำคัญจ่าย" if is_pvn else "ใบเสร็จรับเงิน",
        "is_editable": False,
        "canceled": False,
        "proof_required": needs_proof,
        "is_refund": bool(is_pvn),
    }


def _with_workflow(row: dict[str, Any], *, has_proof: bool = False) -> dict[str, Any]:
    voucno = (row.get("voucno") or row.get("VOUCNO") or "").strip()
    stored = (row.get("noteno") or row.get("NOTENO") or "").strip()
    rem = row.get("reminder") or {}
    canceled = bool(row.get("canceled")) or str(rem.get("status") or "").lower() == "canceled"
    settle = _settle_method_of(row)
    billamt = float(row.get("BILLAMT") or row.get("billamt") or 0)
    disc = float(rem.get("discount_amount") or row.get("DISCOUNT") or 0)
    net = float(row.get("NETAMT") or 0) if voucno else round(billamt - disc, 2)
    is_refund = bool(row.get("is_refund")) or net < -1e-9 or voucno.upper().startswith("PVN")
    out = {
        **row,
        **_workflow_meta(
            voucno=voucno,
            has_proof=has_proof,
            canceled=canceled,
            settle_method=settle,
            is_refund=is_refund,
        ),
        **noteno_meta(stored),
    }
    # Tab 3/4 list columns read top-level settle_method (not reminder.*).
    if settle:
        out["settle_method"] = settle
    if is_refund and not voucno:
        snap = row.get("refund") or {}
        if snap:
            out["refund"] = snap
            out["remaining_refund"] = snap.get("remaining_refund")
            out["refunded_amt"] = snap.get("refunded_amt")
    return out


def _issuer_label_for_identity(ident, *, confirm_unmapped: bool = False) -> str | JSONResponse:
    """Resolve printable preparer name; 409 when staff profile is missing."""
    from src.staff.errors import StaffMappingError
    from src.staff.profiles import issuer_label_for_actor, require_staff_mapping

    line_uid = (ident.line_user_id if ident else "") or ""
    display = (ident.display_name if ident else "") or ""
    try:
        mapped = require_staff_mapping(line_uid, display)
        if mapped.get("issuer_label"):
            return str(mapped["issuer_label"])
    except StaffMappingError as exc:
        if not confirm_unmapped:
            return JSONResponse(
                {"error": exc.message, "code": exc.code},
                status_code=exc.status,
            )
    return issuer_label_for_actor(line_user_id=line_uid, display_name=display)


def _enrich_note_issuer(rem: dict[str, Any] | None) -> dict[str, Any] | None:
    """Prefer snapshotted issuer_label; fall back via created_by LINE user id."""
    if not rem:
        return rem
    out = dict(rem)
    if str(out.get("issuer_label") or "").strip():
        return out
    from src.staff.profiles import issuer_label_for_actor

    label = issuer_label_for_actor(line_user_id=str(out.get("created_by") or ""))
    if label:
        out["issuer_label"] = label
    return out


def _note_totals(header: dict[str, Any], reminder: dict[str, Any] | None) -> dict[str, Any]:
    billamt = float(header.get("BILLAMT") or 0)
    voucno = (header.get("voucno") or header.get("VOUCNO") or "").strip()
    rem = reminder or {}
    if voucno:
        disc = float(header.get("DISCOUNT") or rem.get("discount_amount") or 0)
        net = float(header.get("NETAMT") or 0) or round(billamt - disc, 2)
    else:
        disc = float(rem.get("discount_amount") or 0)
        net = round(billamt - disc, 2)
    return {
        "billcnt": int(header.get("BILLCNT") or 0),
        "billamt": billamt,
        "discount": disc,
        "netamt": net,
        "net_text": baht_text(net),
    }


def _list_voucher_payments(site: str, voucno: str) -> list[dict[str, Any]]:
    rows = list_brdet(site, voucno)
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["settle_method"] = infer_settle_method(
            item.get("CHKNO"),
            bankname=item.get("BANKNAME"),
            acctno=item.get("ACCTNO"),
        )
        out.append(item)
    return out


def _note_detail_response(settings, acctno: str, noteno: str):
    client = get_receive_notes_supabase_client()
    rem = get_note(client, acctno, noteno)
    rem = _enrich_note_issuer(rem)
    include_canceled = bool(rem and str(rem.get("status") or "").lower() == "canceled")
    header = get_note_header(
        settings.site, acctno, noteno, include_canceled=include_canceled
    )
    if not header and rem and include_canceled:
        header = get_note_header(settings.site, acctno, noteno, include_canceled=True)
    if not header:
        return JSONResponse({"error": "not found"}, status_code=404)
    proofs: list[dict[str, Any]] = []
    voucno = (header.get("voucno") or "").strip()
    if voucno:
        proofs = list_folder(client, payment_image_prefix(voucno))
    try:
        try:
            bills = list_note_bills(settings.site, acctno, noteno)
        except RuntimeError:
            bills = []
        payments = _list_voucher_payments(settings.site, voucno) if voucno else []
        debtor = get_debtor(settings.site, acctno)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    totals = _note_totals(header, rem)
    receive_bank = resolve_optional_receive_account(
        (rem or {}).get("receive_bank_key") if rem else None
    )
    canceled = bool(header.get("canceled")) or (
        str((rem or {}).get("status") or "").lower() == "canceled"
    )
    settle = _settle_method_of(
        {
            "reminder": rem,
            "settle_method": (rem or {}).get("settle_method")
            or (payments[0].get("settle_method") if payments else ""),
        }
    )
    done = _proof_done(voucno=voucno, has_proof=bool(proofs), settle_method=settle)
    # Meta-edit enrichment must never 500 the detail/"ดู" view.
    receipt = None
    edit_history: list[dict[str, Any]] = []
    edit_gate = {"needs_accounting_review": False, "reasons": []}
    pay_bank_key = ""
    received_at = str(header.get("VOUCDATE") or "").strip()[:10]
    if voucno:
        try:
            edit_gate = assess_receive_edit_gate(header=header, payments=payments)
        except Exception:
            edit_gate = {"needs_accounting_review": False, "reasons": []}
        try:
            receipt = get_receipt_by_voucno(client, voucno)
        except Exception:
            receipt = None
        try:
            edit_history = list_receipt_edit_audits(client, voucno=voucno)
        except Exception:
            edit_history = []
        pay0 = payments[0] if payments else {}
        channels = list((receipt or {}).get("receipt_channel") or [])
        channel0 = channels[0] if isinstance(channels, list) and channels else {}
        if not isinstance(channel0, dict):
            channel0 = {}
        pay_bank_key = (
            str(channel0.get("receive_bank_key") or "").strip()
            or receive_bank_key_from_gl(pay0.get("ACCTNO") or channel0.get("bank_gl"))
            or receive_bank_key_from_bankname(
                pay0.get("BANKNAME") or channel0.get("bankname")
            )
            or ""
        )
        received_at = (
            str(channel0.get("chkdate") or "").strip()[:10]
            or str((receipt or {}).get("received_at") or "").strip()[:10]
            or str(pay0.get("CHKDATE") or "").strip()[:10]
            or received_at
        )
    return {
        "header": header,
        "bills": bills,
        "payments": payments,
        "reminder": rem,
        "totals": totals,
        "bill_images": [],
        "payment_images": proofs,
        "banks": [],
        "debtor": debtor,
        "receive_bank": receive_bank,
        "canceled": canceled,
        "has_proof": done,
        "settle_method": settle,
        "receipt": receipt,
        "edit_gate": edit_gate,
        "edit_history": edit_history,
        "can_edit_meta": bool(voucno) and not canceled,
        "received_at": received_at,
        "pay_bank_key": pay_bank_key,
        "issue_date": str(header.get("VOUCDATE") or "").strip()[:10] or None,
        **_workflow_meta(
            voucno=voucno,
            has_proof=bool(proofs),
            canceled=canceled,
            settle_method=settle,
        ),
        **noteno_meta(noteno),
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    settings = _settings()
    ident, err = _require(request)
    if err and t:
        try:
            ident = _verify_token(t)
            err = None
        except TokenError:
            pass
    if err and is_tailscale_cg_nat(_client_ip(request)):
        ident = _tailscale_identity()
        err = None
    if err:
        return err
    name = ident.display_name if ident else "operator"
    html = shell_page(
        page(
            user_name=name,
            site=settings.site,
            write_enabled=settings.receive_notes_write_enabled,
            ai_enabled=False,
        ),
        service_id="receive-notes",
        api_base="/receive-notes/_shell",
        user_name=name,
        branch=settings.site,
    )
    resp = HTMLResponse(html)
    if ident and ident.line_user_id != "tailscale":
        _set_session(resp, ident, request=request, has_entry_token=bool(t))
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


@router.get("/api/vendors")
@router.get("/api/debtors")
def api_debtors(request: Request, q: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    try:
        rows = search_debtors(settings.site, q)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return rows


@router.get("/api/bills")
def api_bills(request: Request, acctno: str = "", noteno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct:
        return []
    try:
        if note:
            rows = list_bills_for_edit(settings.site, acct, note)
        else:
            rows = list_pickable_bills(settings.site, acct, include_noted=False)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return rows


@router.get("/api/company-receive-accounts")
@router.get("/api/company-pay-accounts")
def api_company_receive_accounts(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    return list_company_receive_accounts()


@router.get("/api/banks")
def api_banks(request: Request, acctno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    _ = acctno
    return []


@router.get("/api/debtor-summary")
def api_debtor_summary(request: Request, acctno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    try:
        data = debtor_summary(settings.site, acctno)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return data


@router.get("/api/pending")
def api_pending(request: Request):
    """Open/unvouchered notes only. Canceled notes stay on /api/notes for search/audit."""
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    client = get_receive_notes_supabase_client()
    overlays = list_open_notes(client)
    try:
        rows = list_pending_notes(settings.site, overlays)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    out = []
    for row in rows:
        rem = row.get("reminder") or {}
        billamt = float(row.get("BILLAMT") or 0)
        disc = float(rem.get("discount_amount") or 0)
        net = round(billamt - disc, 2)
        enriched = {**row, "stage": "pending"}
        if net < -1e-9:
            snap = note_refund_snapshot(
                acctno=str(row.get("acctno") or ""),
                noteno=str(row.get("noteno") or ""),
                note_net=net,
                client=client,
            )
            enriched["refund"] = snap
            enriched["is_refund"] = True
            enriched["remaining_refund"] = snap.get("remaining_refund")
            enriched["refunded_amt"] = snap.get("refunded_amt")
        out.append(_with_workflow(enriched))
    return out


@router.patch("/api/reminder")
def api_reminder_patch(request: Request, acctno: str, noteno: str, body: ReminderPatch):
    _, err = _require_api(request)
    if err:
        return err
    client = get_receive_notes_supabase_client()
    existing = get_note(client, acctno, noteno) or {}
    if not existing:
        return JSONResponse({"error": "note overlay not found"}, status_code=404)
    patch: dict[str, Any] = {}
    if body.due_date:
        try:
            patch["due_date"] = _parse_due(body.due_date)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
    if body.remark is not None or body.bill_month is not None or body.remark_extra is not None:
        rem_fields = resolve_remark_fields(
            acctno,
            bill_month=body.bill_month,
            remark_extra=body.remark_extra,
            remark=body.remark,
            existing=existing,
        )
        patch.update(rem_fields)
    if body.settle_method is not None:
        try:
            method = _normalize_note_pay_method(body.settle_method)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        patch["settle_method"] = method
    if body.receive_bank_key is not None:
        try:
            patch["receive_bank_key"] = _normalize_receive_bank_key(body.receive_bank_key)
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
    if body.discount_mode is not None or body.discount_input is not None:
        settings = _settings()
        header = get_note_header(settings.site, acctno, noteno)
        billamt = float((header or {}).get("BILLAMT") or 0)
        mode = body.discount_mode if body.discount_mode is not None else existing.get("discount_mode", "amount")
        raw = body.discount_input if body.discount_input is not None else existing.get("discount_input", 0)
        try:
            discount_mode, discount_input, discount_amount = _resolve_discount(
                billamt, mode, float(raw or 0)
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
        patch["discount_mode"] = discount_mode
        patch["discount_input"] = discount_input
        patch["discount_amount"] = discount_amount
    if not patch:
        return existing
    return patch_note(client, acctno, noteno, patch)


@router.post("/api/notes")
def api_create_note(request: Request, body: NoteCreate):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = body.acctno.strip()
    if not body.billnos:
        return JSONResponse({"error": "select at least one bill"}, status_code=400)
    try:
        receive_bank_key = _normalize_receive_bank_key(body.receive_bank_key)
    except ValueError as exc:
        return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
    settle_method = None
    if body.settle_method:
        try:
            settle_method = _normalize_note_pay_method(body.settle_method)
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)

    issuer_label = _issuer_label_for_identity(
        ident, confirm_unmapped=bool(body.confirm_unmapped)
    )
    if isinstance(issuer_label, JSONResponse):
        return issuer_label

    try:
        due = _parse_due(body.due_date)
    except ValueError as exc:
        return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)

    # KSS + Supabase cannot share one ACID tx. Write KSS first, then overlay;
    # if overlay fails, compensate by canceling the unvouchered KSS note.
    try:
        kss = create_receive_note(
            settings=settings,
            acctno=acct,
            acctname=body.acctname.strip(),
            billnos=body.billnos,
            operator=ident.display_name if ident else None,
        )
    except ReceiveNoteWriteError as exc:
        if exc.code == "write_disabled":
            status = 403
        elif exc.code in ("bill_conflict", "stamp_mismatch", "already_vouchered"):
            status = 409
        else:
            status = 400
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)

    note = str(kss.get("noteno") or "").strip()
    billamt = float(kss.get("billamt") or 0)
    try:
        discount_mode, discount_input, discount_amount = _resolve_discount(
            billamt, body.discount_mode, body.discount_input
        )
    except ValueError as exc:
        try:
            cancel_unvouchered_receive_note(settings=settings, acctno=acct, noteno=note)
        except Exception:
            pass
        return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)

    rem_fields = resolve_remark_fields(
        acct,
        bill_month=body.bill_month,
        remark_extra=body.remark_extra,
        remark=body.remark,
    )
    rem_row: dict[str, Any] = {
        "acctno": acct,
        "noteno": note,
        "jourmode": str(kss.get("jourmode") or "1"),
        "due_date": due,
        "discount_mode": discount_mode,
        "discount_input": discount_input,
        "discount_amount": discount_amount,
        "settle_method": settle_method,
        "receive_bank_key": receive_bank_key,
        "status": "open",
        **rem_fields,
        "created_by": ident.line_user_id if ident else None,
        "issuer_label": issuer_label or None,
    }
    client = get_receive_notes_supabase_client()
    try:
        # Upsert: canceled/orphan open overlays must not 500 on note_pkey
        # (create-and-pay double-submit / BN reuse after soft-cancel).
        rem = ensure_open_note(client, rem_row)
    except NoteOverlayConflict as exc:
        rolled_back = False
        rollback_error = None
        try:
            cancel_unvouchered_receive_note(settings=settings, acctno=acct, noteno=note)
            rolled_back = True
        except Exception as cancel_exc:
            rollback_error = str(cancel_exc)
        payload = {
            "error": str(exc),
            "code": exc.code,
            "noteno": note,
            "kss_rolled_back": rolled_back,
        }
        if rollback_error:
            payload["kss_rollback_error"] = rollback_error
        return JSONResponse(payload, status_code=409)
    except Exception as exc:
        rolled_back = False
        rollback_error = None
        try:
            cancel_unvouchered_receive_note(settings=settings, acctno=acct, noteno=note)
            rolled_back = True
        except Exception as cancel_exc:
            rollback_error = str(cancel_exc)
        payload = {
            "error": f"overlay failed: {exc}",
            "code": "reminder_failed",
            "noteno": note,
            "kss_rolled_back": rolled_back,
        }
        if rollback_error:
            payload["kss_rollback_error"] = rollback_error
        return JSONResponse(payload, status_code=500)
    return {**kss, "reminder": rem, **noteno_meta(note)}


@router.get("/api/notes")
def api_list_notes(request: Request, acctno: str = "", noteno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    if (noteno or "").strip():
        acct = (acctno or "").strip()
        if not acct:
            return JSONResponse({"error": "acctno required with noteno"}, status_code=400)
        settings = _settings()
        return _note_detail_response(settings, acct, noteno.strip())
    settings = _settings()
    client = get_receive_notes_supabase_client()
    overlays = list_all_service_notes(client)
    if acctno.strip():
        acct = acctno.strip()
        overlays = [r for r in overlays if (r.get("acctno") or "").strip() == acct]
    open_overlays = [r for r in overlays if str(r.get("status") or "open") == "open"]
    canceled_overlays = [r for r in overlays if str(r.get("status") or "") == "canceled"]
    try:
        pending = list_pending_notes(settings.site, open_overlays)
        vouchered = list_vouchered_notes(settings.site, overlays)
        canceled = list_canceled_notes(settings.site, canceled_overlays)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in pending:
        key = (row.get("acctno", "").strip(), row.get("noteno", "").strip())
        seen.add(key)
        out.append(_with_workflow(row))
    for row in vouchered:
        key = (row.get("acctno", "").strip(), row.get("noteno", "").strip())
        if key in seen:
            continue
        if str((row.get("reminder") or {}).get("status") or "") == "canceled":
            continue
        voucno = (row.get("voucno") or "").strip()
        proofs = list_folder(client, payment_image_prefix(voucno)) if voucno else []
        has_proof = bool(proofs)
        settle = _settle_method_of(row)
        out.append(
            _with_workflow(
                {
                    **row,
                    "has_proof": has_proof or _proof_done(
                        voucno=voucno, has_proof=has_proof, settle_method=settle
                    ),
                    "payment_images": proofs,
                },
                has_proof=has_proof,
            )
        )
    for row in canceled:
        key = (row.get("acctno", "").strip(), row.get("noteno", "").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(_with_workflow({**row, "canceled": True}))
    out.sort(
        key=lambda x: (
            (x.get("reminder") or {}).get("due_date") or "",
            x.get("noteno") or "",
        )
    )
    return out


@router.patch("/api/notes")
def api_update_note(request: Request, acctno: str, noteno: str, body: NoteUpdate):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = acctno.strip()
    note = noteno.strip()
    if not body.billnos:
        return JSONResponse({"error": "select at least one bill"}, status_code=400)

    client = get_receive_notes_supabase_client()
    rem = get_note(client, acct, note)
    if not rem:
        return JSONResponse({"error": "reminder not found"}, status_code=404)

    header = get_note_header(settings.site, acct, note)
    if not header:
        return JSONResponse({"error": "note not found in KSS"}, status_code=404)
    if (header.get("voucno") or "").strip() or str(header.get("VOUCED") or "N").strip().upper() == "Y":
        return JSONResponse({"error": "note is not editable", "code": "not_editable"}, status_code=409)

    try:
        kss = update_receive_note(
            settings=settings,
            acctno=acct,
            noteno=note,
            billnos=body.billnos,
            operator=ident.display_name if ident else None,
        )
    except ReceiveNoteWriteError as exc:
        status = 409 if exc.code == "not_editable" else 400
        if exc.code == "write_disabled":
            status = 403
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)

    billamt = float(kss.get("billamt") or 0)
    patch: dict[str, Any] = {}
    if body.due_date:
        try:
            patch["due_date"] = _parse_due(body.due_date)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
    if body.remark is not None or body.bill_month is not None or body.remark_extra is not None:
        rem_fields = resolve_remark_fields(
            acct,
            bill_month=body.bill_month,
            remark_extra=body.remark_extra,
            remark=body.remark,
            existing=rem,
        )
        patch.update(rem_fields)
    if body.settle_method is not None:
        try:
            method = _normalize_note_pay_method(body.settle_method)
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
        patch["settle_method"] = method
    if body.receive_bank_key is not None:
        try:
            patch["receive_bank_key"] = _normalize_receive_bank_key(body.receive_bank_key)
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
    if body.discount_mode is not None or body.discount_input is not None:
        mode = body.discount_mode if body.discount_mode is not None else rem.get("discount_mode", "amount")
        raw = body.discount_input if body.discount_input is not None else rem.get("discount_input", 0)
        try:
            discount_mode, discount_input, discount_amount = _resolve_discount(
                billamt, mode, float(raw or 0)
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc), "code": "validation"}, status_code=400)
        patch["discount_mode"] = discount_mode
        patch["discount_input"] = discount_input
        patch["discount_amount"] = discount_amount

    updated = patch_note(client, acct, note, patch) if patch else rem
    return {**kss, "reminder": updated, **_workflow_meta()}


@router.delete("/api/notes")
def api_cancel_note(request: Request, acctno: str = "", noteno: str = ""):
    """Soft-cancel unpaid note in both systems: KSS CANCELED='Y' + overlay status=canceled."""
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        return JSONResponse({"error": "acctno and noteno required"}, status_code=400)

    client = get_receive_notes_supabase_client()
    rem = get_note(client, acct, note)
    header = get_note_header(settings.site, acct, note, include_canceled=True)

    if rem and str(rem.get("status") or "").lower() == "canceled":
        return {
            "acctno": acct,
            "noteno": note,
            "canceled": True,
            "already_canceled": True,
            "reminder": rem,
            **_workflow_meta(canceled=True),
        }

    if header:
        if (header.get("voucno") or "").strip() or str(header.get("VOUCED") or "N").strip().upper() == "Y":
            return JSONResponse(
                {
                    "error": "ไม่สามารถยกเลิกใบวางบิลที่มีการรับชำระแล้ว",
                    "code": "already_vouchered",
                },
                status_code=409,
            )
        if header.get("canceled"):
            # KSS already canceled — still mark overlay if needed
            pass
    elif not rem:
        return JSONResponse({"error": "note not found"}, status_code=404)

    kss_result: dict[str, Any] = {"canceled": False, "reason": "not_in_kss"}
    # Always attempt KSS cancel when note may exist (do not rely on non-canceled-only lookup).
    if header and not header.get("canceled"):
        try:
            kss_result = cancel_unvouchered_receive_note(
                settings=settings, acctno=acct, noteno=note
            )
        except ReceiveNoteWriteError as exc:
            status = 409 if exc.code in ("already_vouchered", "not_editable") else 400
            if exc.code == "write_disabled":
                status = 403
            if exc.code == "already_vouchered":
                return JSONResponse(
                    {
                        "error": "ไม่สามารถยกเลิกใบวางบิลที่มีการรับชำระแล้ว",
                        "code": exc.code,
                    },
                    status_code=409,
                )
            return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)
    elif header and header.get("canceled"):
        kss_result = {"acctno": acct, "noteno": note, "canceled": True, "reason": "already_canceled"}
    else:
        # Overlay-only orphan: still try writer (may find KSS when active-header lookup missed).
        try:
            kss_result = cancel_unvouchered_receive_note(
                settings=settings, acctno=acct, noteno=note
            )
        except ReceiveNoteWriteError as exc:
            if exc.code == "write_disabled":
                return JSONResponse({"error": str(exc), "code": exc.code}, status_code=403)
            if exc.code == "already_vouchered":
                return JSONResponse(
                    {
                        "error": "ไม่สามารถยกเลิกใบวางบิลที่มีการรับชำระแล้ว",
                        "code": exc.code,
                    },
                    status_code=409,
                )
            # not_found → keep going to mark overlay canceled
            kss_result = {"acctno": acct, "noteno": note, "canceled": False, "reason": exc.code}

    reminder = rem
    try:
        if rem:
            reminder = patch_note(client, acct, note, {"status": "canceled"})
        elif kss_result.get("canceled") or (header and header.get("canceled")):
            # Recreate overlay so new system keeps doc no. with red ยกเลิก
            # (covers prior bug that deleted overlay while KSS stayed open).
            reminder = insert_note(
                client,
                {
                    "acctno": acct,
                    "noteno": note,
                    "jourmode": str((header or {}).get("JOURMODE") or "1"),
                    "status": "canceled",
                    "due_date": None,
                },
            )
    except Exception as exc:
        return JSONResponse(
            {
                "error": f"KSS canceled but overlay status update failed: {exc}",
                "code": "reminder_cancel_failed",
                "acctno": acct,
                "noteno": note,
                "kss": kss_result,
            },
            status_code=500,
        )

    canceled_ok = bool(kss_result.get("canceled")) or (
        reminder is not None and str(reminder.get("status") or "").lower() == "canceled"
    )
    return {
        "acctno": acct,
        "noteno": note,
        "canceled": canceled_ok,
        "kss": kss_result,
        "reminder": reminder,
        "reminder_deleted": False,
        "images_removed": 0,
        **_workflow_meta(canceled=True),
    }


def _voucher_response_from_kss(
    *,
    result: dict[str, Any],
    rem: dict[str, Any] | None,
    method: str,
    pay_bank_key: str,
) -> dict[str, Any]:
    recv_acct = resolve_company_receive_account(pay_bank_key)
    voucno = str(result.get("voucno") or "").strip()
    needs_proof = proof_required(voucno=voucno, settle_method=method)
    return {
        **result,
        "reminder": rem,
        "settle_method": method,
        "pay_bank": recv_acct["key"],
        "receive_bank_key": recv_acct["key"],
        "proof_required": needs_proof,
        "awaiting_tiger": False,
        **_workflow_meta(
            voucno=voucno,
            has_proof=False,
            settle_method=method,
        ),
    }


def _tiger_pending_response(
    *,
    started: dict[str, Any],
    rem: dict[str, Any] | None,
    method: str = "cash",
) -> dict[str, Any]:
    receipt = started.get("receipt") or {}
    attempt = started.get("tiger_attempt") or {}
    return {
        "awaiting_tiger": True,
        "receipt_id": receipt.get("id"),
        "noteno": receipt.get("noteno"),
        "tiger_attempt_id": attempt.get("id") or receipt.get("tiger_attempt_id"),
        "tiger_payment_id": attempt.get("tiger_payment_id")
        or receipt.get("tiger_payment_id"),
        "tiger_payment_no": attempt.get("tiger_payment_no")
        or receipt.get("tiger_payment_no"),
        "tiger_status": attempt.get("status"),
        "reminder": rem,
        "settle_method": method,
        "proof_required": False,
        "stage": "awaiting_tiger",
        "workflow_status": "รอ Tiger",
        "is_editable": False,
        "canceled": False,
        "receipt": receipt,
        "tiger_attempt": attempt,
    }


def _attach_refund_voucher_qr(pending: dict[str, Any], attempt: dict[str, Any] | None) -> None:
    """Expose KCN-style voucher QR for staff to scan at Tiger cashbox."""
    from src.receive_notes.tiger import ar_refund_voucher_display

    voucher = ar_refund_voucher_display(attempt)
    if not voucher:
        return
    pending["voucher"] = voucher
    if voucher.get("voucher_num") and not pending.get("tiger_payment_no"):
        pending["tiger_payment_no"] = voucher.get("voucher_num")


def _refund_response(
    *,
    started: dict[str, Any],
    rem: dict[str, Any] | None,
    method: str,
    pay_bank_key: str,
) -> dict[str, Any]:
    if started.get("awaiting_tiger"):
        pending = _tiger_pending_response(started=started, rem=rem, method=method)
        pending["is_refund"] = True
        pending["workflow_status"] = "รอ Tiger คืนเงินสด"
        pending["remaining_refund"] = started.get("remaining_refund")
        pending["refunded_amt"] = started.get("refunded_amt")
        attempt = started.get("tiger_attempt") or {}
        if attempt.get("voucher_num") and not pending.get("tiger_payment_no"):
            pending["tiger_payment_no"] = attempt.get("voucher_num")
        _attach_refund_voucher_qr(pending, attempt)
        return pending

    kss = started.get("kss") or {}
    voucno = str(kss.get("voucno") or "").strip()
    recv_acct = resolve_company_receive_account(pay_bank_key)
    needs_proof = proof_required(voucno=voucno, settle_method=method) if voucno else False
    # Partial refund: note stays open (รอคืนเงิน); no KSS PVN yet.
    if kss.get("partial") or kss.get("kss_deferred") or not voucno:
        return {
            **kss,
            "reminder": rem,
            "settle_method": method,
            "pay_bank": recv_acct["key"],
            "receive_bank_key": recv_acct["key"],
            "proof_required": False,
            "awaiting_tiger": False,
            "is_refund": True,
            "partial": True,
            "remaining_refund": started.get("remaining_refund", kss.get("remaining_refund")),
            "refunded_amt": started.get("refunded_amt", kss.get("refunded_amt")),
            "stage": "pending",
            "workflow_status": "รอคืนเงิน",
            "is_editable": True,
            "canceled": False,
            "receipt": started.get("receipt"),
        }
    return {
        **_voucher_response_from_kss(
            result=kss,
            rem=rem,
            method=method,
            pay_bank_key=pay_bank_key,
        ),
        "is_refund": True,
        "proof_required": needs_proof,
        "workflow_status": "ใบสำคัญจ่าย",
        "remaining_refund": 0.0,
    }


@router.patch("/api/vouchers/meta")
def api_edit_voucher_meta(request: Request, body: VoucherMetaEdit):
    """Correct receive date / remark / bank on an existing voucher (no re-cut)."""
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = body.acctno.strip()
    note = body.noteno.strip()
    if not acct or not note:
        return JSONResponse({"error": "acctno and noteno required"}, status_code=400)
    if (
        body.received_at is None
        and body.remark is None
        and body.receive_bank_key is None
    ):
        return JSONResponse({"error": "nothing to update"}, status_code=400)
    operator = ident.display_name if ident else None
    try:
        result = edit_vouchered_receive_meta(
            acctno=acct,
            noteno=note,
            received_at=body.received_at,
            remark=body.remark,
            receive_bank_key=body.receive_bank_key,
            accounting_reviewed=bool(body.accounting_reviewed),
            operator=operator,
            settings=settings,
        )
    except ReceiveServiceError as exc:
        status = 400
        if exc.code in ("not_found",):
            status = 404
        elif exc.code in ("needs_accounting_review", "not_editable", "not_vouchered"):
            status = 409
        elif exc.code == "write_disabled":
            status = 403
        elif exc.code == "audit_unavailable":
            status = 503
        payload: dict[str, Any] = {"error": str(exc), "code": exc.code}
        if exc.code == "needs_accounting_review":
            try:
                header = get_note_header(settings.site, acct, note)
                voucno = str((header or {}).get("voucno") or "").strip()
                payments = _list_voucher_payments(settings.site, voucno) if voucno else []
                payload["edit_gate"] = assess_receive_edit_gate(
                    header=header, payments=payments
                )
            except Exception:
                payload["edit_gate"] = {"needs_accounting_review": True, "reasons": []}
        return JSONResponse(payload, status_code=status)
    return result


@router.post("/api/vouchers")
def api_create_voucher(request: Request, body: VoucherCreate):
    """Record receipt voucher or customer credit refund.

    Positive net → รับชำระ (cash via Tiger payment). Negative net → คืนเงินลูกค้า
    (cash via Tiger voucher / KCN pattern). KSS PVN only after real payout confirm.
    """
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    acct = body.acctno.strip()
    note = body.noteno.strip()
    client = get_receive_notes_supabase_client()
    rem = get_note(client, acct, note)
    if not rem:
        return JSONResponse({"error": "reminder not found for this note"}, status_code=404)

    header = get_note_header(settings.site, acct, note)
    if not header:
        return JSONResponse({"error": "note not found in KSS"}, status_code=404)
    if (header.get("voucno") or "").strip() or str(header.get("VOUCED") or "N").strip().upper() == "Y":
        return JSONResponse(
            {"error": "note already vouchered", "code": "already_vouchered"},
            status_code=409,
        )

    billamt = float(header.get("BILLAMT") or 0)
    disc = float(rem.get("discount_amount") or 0)
    # Same rule as _resolve_discount: negative BILLAMT is a valid note total.
    if billamt >= 0 and disc - billamt > 1e-9:
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

    try:
        chkamt = float(body.chkamt)
    except (TypeError, ValueError):
        return JSONResponse({"error": "CHKAMT required"}, status_code=400)

    pay_bank_key = (
        (body.pay_bank or "").strip()
        or (body.receive_bank_key or "").strip()
        or DEFAULT_RECEIVE_BANK_KEY
    )
    chkdate = (body.chkdate or "").strip() or datetime.now(_BKK).date().isoformat()

    try:
        bills = list_note_bills(settings.site, acct, note)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    if not bills:
        return JSONResponse({"error": "no bills on note"}, status_code=400)

    acctname = str(header.get("acctname") or header.get("ACCTNAME") or "").strip()
    operator = ident.display_name if ident else None

    # ---- Customer credit refund (negative BN/BNN) ----
    if net < -1e-9:
        refund_amt = abs(float(chkamt))
        if refund_amt <= 0:
            return JSONResponse({"error": "refund amount must be > 0"}, status_code=400)
        try:
            started = start_note_refund(
                acctno=acct,
                acctname=acctname,
                noteno=note,
                bills=bills,
                refund_amt=refund_amt,
                note_net=net,
                settle_method=method,
                chkno=chkno,
                chkdate=chkdate,
                receive_bank_key=pay_bank_key,
                discount=disc,
                operator=operator,
                settings=settings,
            )
        except ReceiveServiceError as exc:
            status = 409 if exc.code in (
                "already_paid",
                "tiger_busy",
                "active_attempt",
                "already_completed",
            ) else 400
            if exc.code == "write_disabled":
                status = 403
            return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)
        return _refund_response(
            started=started, rem=rem, method=method, pay_bank_key=pay_bank_key
        )

    # ---- Normal receive (positive / zero net) ----
    if chkamt <= 0 and net > 1e-9:
        return JSONResponse({"error": "CHKAMT must be > 0"}, status_code=400)
    if chkamt - net > 0.01:
        return JSONResponse(
            {"error": f"CHKAMT ({chkamt}) exceeds net payable ({net})"},
            status_code=400,
        )

    bill_allocations = [
        {
            "billno": str(b.get("BILLNO") or "").strip(),
            "allocate_amt": float(b.get("AFTERTAX") or 0),
        }
        for b in bills
        if str(b.get("BILLNO") or "").strip()
    ]

    if method == "cash":
        try:
            started = start_note_cash_via_tiger(
                acctno=acct,
                acctname=acctname,
                noteno=note,
                bill_allocations=bill_allocations,
                chkamt=chkamt,
                discount=disc,
                chkdate=chkdate,
                operator=operator,
                settings=settings,
            )
        except ReceiveServiceError as exc:
            status = 409 if exc.code in ("already_paid", "tiger_busy", "active_attempt") else 400
            if exc.code == "write_disabled":
                status = 403
            return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)

        # Rare race: Tiger already succeeded between create and return.
        if not started.get("awaiting_tiger") and started.get("kss"):
            rem = patch_note(
                client,
                acct,
                note,
                {"status": "received", "settle_method": "cash"},
            )
            return _voucher_response_from_kss(
                result=started["kss"],
                rem=rem,
                method="cash",
                pay_bank_key=pay_bank_key,
            )
        return _tiger_pending_response(started=started, rem=rem, method="cash")

    brdet_lines: list[dict[str, Any]] = []
    if chkamt > 1e-9:
        try:
            brdet_lines = [
                brdet_line_from_payment(
                    settle_method=method,
                    chkno=chkno,
                    chkamt=chkamt,
                    chkdate=chkdate,
                    receive_bank_key=pay_bank_key,
                )
            ]
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    try:
        result = create_receipt_voucher(
            settings=settings,
            acctno=acct,
            acctname=acctname,
            bill_allocations=bill_allocations,
            brdet_lines=brdet_lines,
            discount=disc,
            noteno=note,
            operator=operator,
        )
    except ReceiveNoteWriteError as exc:
        status = 409 if exc.code == "already_vouchered" else 400
        if exc.code == "write_disabled":
            status = 403
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)

    rem = patch_note(
        client,
        acct,
        note,
        {
            "status": "received",
            "settle_method": method,
        },
    )
    return _voucher_response_from_kss(
        result=result,
        rem=rem,
        method=method,
        pay_bank_key=pay_bank_key,
    )


@router.get("/api/vouchers/tiger-status")
def api_tiger_voucher_status(request: Request, receipt_id: str = ""):
    """Poll Tiger cash attempt / refund voucher; writes KSS only after success."""
    ident, err = _require_api(request)
    if err:
        return err
    rid = (receipt_id or "").strip()
    if not rid:
        return JSONResponse({"error": "receipt_id required"}, status_code=400)

    from src.receive_notes.db import get_receipt

    client = get_receive_notes_supabase_client()
    receipt0 = get_receipt(client, rid)
    is_refund = bool(receipt0) and float((receipt0 or {}).get("netamt") or 0) < -1e-9
    sync_fn = sync_tiger_refund if is_refund else sync_tiger_receipt

    try:
        synced = sync_fn(
            receipt_id=rid,
            operator=ident.display_name if ident else None,
        )
    except ReceiveServiceError as exc:
        status = 404 if exc.code == "not_found" else 409
        if exc.code == "tiger_pending":
            status = 202
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=status)

    receipt = synced.get("receipt") or receipt0 or {}
    attempt = synced.get("tiger_attempt") or {}
    if synced.get("awaiting_tiger"):
        tiger_no = (
            attempt.get("voucher_num")
            or attempt.get("tiger_payment_no")
            or receipt.get("tiger_payment_no")
        )
        pending = {
            "awaiting_tiger": True,
            "done": False,
            "is_refund": is_refund,
            "receipt_id": rid,
            "tiger_status": synced.get("tiger_status"),
            "tiger_attempt_id": attempt.get("id") or receipt.get("tiger_attempt_id"),
            "tiger_payment_no": tiger_no,
            "settle_method": "cash",
            "proof_required": False,
            "stage": "awaiting_tiger",
            "workflow_status": "รอ Tiger คืนเงินสด" if is_refund else "รอ Tiger",
            "receipt": receipt,
            "tiger_attempt": attempt,
        }
        if is_refund:
            _attach_refund_voucher_qr(pending, attempt)
        return pending

    if synced.get("failed"):
        return JSONResponse(
            {
                "awaiting_tiger": False,
                "done": False,
                "failed": True,
                "is_refund": is_refund,
                "error": f"Tiger {synced.get('tiger_status') or 'failed'}",
                "code": "tiger_failed",
                "receipt_id": rid,
                "tiger_status": synced.get("tiger_status"),
                "receipt": receipt,
            },
            status_code=409,
        )

    kss = synced.get("kss") or {}
    if is_refund:
        return _refund_response(
            started={
                "awaiting_tiger": False,
                "kss": kss,
                "receipt": receipt,
                "remaining_refund": kss.get("remaining_refund"),
                "refunded_amt": kss.get("refunded_amt"),
            },
            rem=get_note(
                client,
                str(receipt.get("acctno") or ""),
                str(receipt.get("noteno") or ""),
            ),
            method="cash",
            pay_bank_key=DEFAULT_RECEIVE_BANK_KEY,
        )

    voucno = str(kss.get("voucno") or receipt.get("voucno") or "").strip()
    acct = str(receipt.get("acctno") or "").strip()
    note = str(receipt.get("noteno") or "").strip()
    rem = None
    if acct and note:
        rem = patch_note(
            client,
            acct,
            note,
            {"status": "received", "settle_method": "cash"},
        )
    return _voucher_response_from_kss(
        result={
            "voucno": voucno,
            "noteno": note,
            "acctno": acct,
            **{k: v for k, v in kss.items() if k not in ("voucno", "noteno", "acctno")},
        },
        rem=rem,
        method="cash",
        pay_bank_key=DEFAULT_RECEIVE_BANK_KEY,
    )


@router.get("/api/vouchered")
def api_vouchered(request: Request, proof: str = "all"):
    """Vouchered notes from this service. proof=awaiting|done|all."""
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    client = get_receive_notes_supabase_client()
    overlays = list_all_service_notes(client)
    try:
        rows = list_vouchered_notes(settings.site, overlays)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    mode = (proof or "all").strip().lower()
    if mode not in ("all", "awaiting", "done"):
        mode = "all"
    out = []
    for row in rows:
        voucno = (row.get("voucno") or "").strip()
        proofs = list_folder(client, payment_image_prefix(voucno)) if voucno else []
        has_proof = bool(proofs)
        settle = _settle_method_of(row)
        done = _proof_done(voucno=voucno, has_proof=has_proof, settle_method=settle)
        if mode == "awaiting" and done:
            continue
        if mode == "done" and not done:
            continue
        out.append(
            _with_workflow(
                {
                    **row,
                    "payment_images": proofs,
                    "has_proof": done,
                },
                has_proof=has_proof,
            )
        )
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
    name = safe_storage_filename(file.filename, default="proof.jpg")
    path = f"{prefix}/{name}"
    client = get_receive_notes_supabase_client()
    try:
        upload_bytes(
            client,
            path=path,
            data=data,
            content_type=file.content_type or "image/jpeg",
        )
    except Exception as exc:
        return JSONResponse({"error": "upload failed", "detail": str(exc)}, status_code=400)
    return {"path": path, "url": public_url(path)}


@router.get("/api/images/payment")
def api_list_payment_images(request: Request, voucno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    client = get_receive_notes_supabase_client()
    return list_folder(client, payment_image_prefix(voucno))


@router.delete("/api/images/payment")
def api_delete_payment_image(request: Request, voucno: str = "", path: str = ""):
    """Remove one payment proof image. Refuses if it would leave the voucher with no image."""
    _, err = _require_api(request)
    if err:
        return err
    vo = (voucno or "").strip()
    rel = (path or "").strip().lstrip("/")
    if not vo:
        return JSONResponse({"error": "voucno required"}, status_code=400)
    if not rel:
        return JSONResponse({"error": "path required"}, status_code=400)
    prefix = payment_image_prefix(vo).strip("/")
    if not (rel == prefix or rel.startswith(prefix + "/")):
        return JSONResponse({"error": "path not under this voucher"}, status_code=400)
    client = get_receive_notes_supabase_client()
    existing = list_folder(client, prefix)
    if not any((item.get("path") or "").lstrip("/") == rel for item in existing):
        return JSONResponse({"error": "image not found"}, status_code=404)
    if len(existing) <= 1:
        return JSONResponse(
            {"error": "cannot remove last payment image", "code": "last_image"},
            status_code=400,
        )
    remove_paths(client, [rel])
    remaining = list_folder(client, prefix)
    return {"deleted": rel, "remaining": remaining, "has_proof": bool(remaining)}


@router.delete("/api/images/bill")
def api_delete_bill_image(
    request: Request,
    acctno: str = "",
    noteno: str = "",
    path: str = "",
):
    """AR create does not use bill images — no-op for forked UI."""
    _, err = _require_api(request)
    if err:
        return err
    _ = (acctno, noteno, path)
    return {"deleted": path or "", "remaining": []}


@router.get("/api/images/bill")
def api_list_bill_images(request: Request, acctno: str = "", noteno: str = ""):
    _, err = _require_api(request)
    if err:
        return err
    _ = (acctno, noteno)
    return []


@router.post("/api/ai/verify-payment")
async def api_ai_verify_payment(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    return JSONResponse({"error": "ai_disabled", "code": "ai_disabled"}, status_code=503)


@router.post("/api/ai/scan-bills")
async def api_ai_scan_bills(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    return JSONResponse({"error": "ai_disabled", "code": "ai_disabled"}, status_code=503)
