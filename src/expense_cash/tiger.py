from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import quote

from sqlalchemy.engine import Engine
from supabase import create_client

from src.tiger_pay import voucher_repos
from src.tiger_pay.qr import render_qr_image_data_uri
from src.tiger_pay.submitter import normalize_submitter, submitter_payload
from src.tiger_pay.voucher_api import (
    TigerVoucherApiError,
    extract_voucher_display,
    extract_voucher_num,
    get_voucher_api_client,
    normalize_voucher_status,
)
from src.tiger_pay.voucher_service import (
    companion_voucher_from_attempt,
    new_voucher_attempt_id,
    tiger_voucher_create_amount,
)

logger = logging.getLogger("kcw.expense_cash.tiger")

QR_BUCKET = os.getenv("SUPABASE_IMAGE_BUCKET", "pictures")
QR_FOLDER = "expense-cash"


class ExpenseCashTigerError(Exception):
    def __init__(self, message: str, *, code: str = "tiger_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def expense_cash_pos_bill_id(request_id: str) -> str:
    return f"expense-cash:{request_id}"


def _supabase():
    url = (os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise ExpenseCashTigerError(
            "Supabase not configured for QR upload",
            code="supabase_missing",
        )
    return create_client(url, key)


def upload_qr_png(*, request_id: str, voucher_num: str) -> str:
    """Render voucher_num QR and upload; return public HTTPS URL for LINE."""
    data_uri = render_qr_image_data_uri(str(voucher_num))
    # data:image/png;base64,...
    b64 = data_uri.split(",", 1)[1]
    import base64

    png = base64.b64decode(b64)
    path = f"{QR_FOLDER}/{request_id}.png"
    client = _supabase()
    client.storage.from_(QR_BUCKET).upload(
        path,
        png,
        file_options={"content-type": "image/png", "upsert": "true"},
    )
    base = (os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_URL") or "").rstrip("/")
    return f"{base}/storage/v1/object/public/{QR_BUCKET}/{quote(path, safe='/')}?v={quote(voucher_num)}"


def start_expense_cash_voucher(
    engine: Engine,
    *,
    request_id: str,
    short_code: int,
    amount: float | int,
    reason: str,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    """Create Tiger voucher for an approved cash request. Returns attempt + qr_url."""
    pos_bill_id = expense_cash_pos_bill_id(request_id)
    bill_number = f"EXC{int(short_code)}"[:40]
    amount_value = tiger_voucher_create_amount(amount)

    submitted_by, submitted_by_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    submitter = submitter_payload(
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )

    completed = voucher_repos.get_used_voucher_for_bill(engine, pos_bill_id)
    if completed:
        display = companion_voucher_from_attempt(completed) or {}
        qr_url = None
        voucher_num = completed.get("voucher_num")
        if voucher_num:
            try:
                qr_url = upload_qr_png(request_id=request_id, voucher_num=str(voucher_num))
            except Exception:
                logger.exception("QR re-upload failed for existing used voucher")
        return {
            "attempt": completed,
            "voucher": display,
            "qr_image_url": qr_url,
            "already_completed": True,
        }

    existing = voucher_repos.get_active_voucher_for_bill(engine, pos_bill_id)
    if existing:
        display = companion_voucher_from_attempt(existing) or {}
        voucher_num = existing.get("voucher_num")
        qr_url = None
        if voucher_num:
            try:
                qr_url = upload_qr_png(request_id=request_id, voucher_num=str(voucher_num))
            except Exception:
                logger.exception("QR re-upload failed for active voucher")
        return {
            "attempt": existing,
            "voucher": display,
            "qr_image_url": qr_url,
            "already_active": True,
        }

    attempt_id = new_voucher_attempt_id()
    attempt = voucher_repos.create_voucher_attempt(
        engine,
        attempt_id=attempt_id,
        pos_bill_id=pos_bill_id,
        pos_bill_number=bill_number,
        amount=amount_value,
        status="creating",
        raw_status="creating",
        ref_num=bill_number,
        submitted_by=submitted_by,
        submitted_by_name=submitted_by_name,
    )
    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status="creating",
        payload={
            "action": "expense_cash_voucher_created",
            "request_id": request_id,
            "short_code": short_code,
            "tiger_amount": amount_value,
            **submitter,
        },
        event_key=f"api:expense_cash_created:{attempt_id}",
    )

    client = get_voucher_api_client()
    note = (reason or f"Expense cash #{short_code}")[:100]
    try:
        create_result = client.create_voucher(
            amount=amount_value,
            ref_num=bill_number,
            note=note,
            # Same Tiger path as CN / AR refund; note carries expense context.
            category="CN",
        )
    except TigerVoucherApiError as exc:
        voucher_repos.update_voucher_attempt(
            engine,
            attempt_id,
            status="failed",
            raw_status="failed",
            error_message=exc.message,
            raw_create_response={
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
        )
        raise ExpenseCashTigerError(
            f"Tiger create failed: {exc.message}",
            code="tiger_create_failed",
        ) from exc

    raw = create_result.get("raw") or create_result
    voucher_num = extract_voucher_num(raw)
    display = extract_voucher_display(raw)
    raw_status = str(display.get("raw_status") or "pending")
    status = normalize_voucher_status(raw_status)
    if status == "unknown":
        status = "pending"

    updated = voucher_repos.update_voucher_attempt(
        engine,
        attempt_id,
        status=status,
        raw_status=raw_status,
        voucher_num=voucher_num,
        ref_num=bill_number,
        raw_create_response=raw if isinstance(raw, dict) else {"raw": raw},
        clear_error=True,
    )
    voucher_repos.insert_voucher_event(
        engine,
        voucher_attempt_id=attempt_id,
        source="api",
        status=status,
        payload={
            "action": "api_response_received",
            "voucher_num": voucher_num,
            "create_response": raw,
        },
        event_key=f"api:expense_cash_create_response:{attempt_id}:{voucher_num or raw_status}",
    )

    attempt_out = updated or attempt
    qr_url = None
    if voucher_num:
        try:
            qr_url = upload_qr_png(request_id=request_id, voucher_num=str(voucher_num))
        except Exception as exc:
            logger.exception("QR upload failed")
            raise ExpenseCashTigerError(
                f"QR upload failed: {exc}",
                code="qr_upload_failed",
            ) from exc

    return {
        "attempt": attempt_out,
        "voucher": companion_voucher_from_attempt(attempt_out),
        "qr_image_url": qr_url,
    }
