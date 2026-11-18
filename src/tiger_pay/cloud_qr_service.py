from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from src.companion.bills import get_open_bill
from src.tiger_pay import cloud_qr_repos, repos
from src.tiger_pay.backoffice_qr import (
    TigerBackOfficeQrClient,
    TigerBackOfficeQrError,
    get_backoffice_qr_client,
)
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.payload import omit_qr_images
from src.tiger_pay.qr import extract_companion_qr, render_qr_image_data_uri
from src.tiger_pay.submitter import normalize_submitter

logger = logging.getLogger("kcw.tiger_pay.cloud_qr")

CLOUD_QR_PAYMENT_TYPE = "cloud_qr"


class CloudQrServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "cloud_qr_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


def new_cloud_qr_id() -> str:
    import uuid

    return uuid.uuid4().hex[:20]


def companion_qr_from_cloud_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    raw = row.get("qr_raw_data")
    raw_text = raw.strip() if isinstance(raw, str) else ""
    image_raw = row.get("qr_image")
    image = None
    if isinstance(image_raw, str) and image_raw.strip():
        image = image_raw.strip()
        if not image.startswith("data:"):
            image = f"data:image/png;base64,{image}"
    if image is None and raw_text:
        image = render_qr_image_data_uri(raw_text)
    if image is None and not raw_text:
        return None
    return {
        "image": image,
        "raw_data": raw_text or None,
        "status": str(row.get("status") or "").strip() or None,
        "payment_gateway": get_tiger_pay_settings().tiger_backoffice_qr_gateway,
        "transaction_id": row.get("uuid"),
        "ref_no_1": row.get("ref1"),
        "ref_no_2": row.get("ref2"),
    }


def _public_cloud_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if out.get("raw_create_response") is not None:
        out["raw_create_response"] = omit_qr_images(out["raw_create_response"])
    if out.get("raw_status_response") is not None:
        out["raw_status_response"] = omit_qr_images(out["raw_status_response"])
    if out.get("qr_image") and isinstance(out["qr_image"], str) and len(out["qr_image"]) > 200:
        out["qr_image"] = None
        out["qr_image_omitted"] = True
    return out


def get_cloud_qr_detail(engine: Engine, payment_id: str) -> dict[str, Any]:
    row = cloud_qr_repos.get_cloud_qr_payment(engine, payment_id)
    if not row:
        raise CloudQrServiceError("Cloud QR payment not found", code="not_found")
    return {
        "attempt": _public_cloud_row(row),
        "cloud_qr": _public_cloud_row(row),
        "events": [],
        "qr": companion_qr_from_cloud_row(row),
        "payment_type": CLOUD_QR_PAYMENT_TYPE,
    }


def send_cloud_qr_for_bill(
    engine: Engine,
    pos_bill_id: str,
    *,
    client: TigerBackOfficeQrClient | None = None,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    submitted_by, submitted_by_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )

    bill = get_open_bill(pos_bill_id)
    if bill is None:
        raise CloudQrServiceError("POS bill not found", code="bill_not_found")
    if bill.kind == "payout":
        raise CloudQrServiceError(
            "CN payout bills use voucher cash-return, not payment",
            code="not_collect_bill",
        )

    if repos.get_successful_attempt_for_bill(engine, pos_bill_id):
        raise CloudQrServiceError(
            "Bill already has a completed payment",
            code="payment_already_completed",
        )
    if repos.get_active_attempt_for_bill(engine, pos_bill_id):
        raise CloudQrServiceError(
            "Bill already has an active payment attempt",
            code="active_attempt_exists",
        )
    if cloud_qr_repos.get_successful_cloud_qr_for_bill(engine, pos_bill_id):
        raise CloudQrServiceError(
            "Bill already has a completed cloud QR payment",
            code="payment_already_completed",
        )
    if cloud_qr_repos.get_active_cloud_qr_for_bill(engine, pos_bill_id):
        raise CloudQrServiceError(
            "Bill already has an active cloud QR payment",
            code="active_attempt_exists",
        )

    settings = get_tiger_pay_settings()
    if not settings.tiger_box_serial.strip():
        raise CloudQrServiceError(
            "TIGER_BOX_SERIAL is not configured",
            code="cloud_qr_not_configured",
        )

    payment_id = new_cloud_qr_id()
    try:
        row = cloud_qr_repos.create_cloud_qr_payment(
            engine,
            payment_id=payment_id,
            pos_bill_id=bill.id,
            pos_bill_number=bill.bill_number,
            amount=bill.amount,
            status="sending",
            submitted_by=submitted_by,
            submitted_by_name=submitted_by_name,
        )
    except IntegrityError as exc:
        if cloud_qr_repos.get_successful_cloud_qr_for_bill(engine, pos_bill_id):
            raise CloudQrServiceError(
                "Bill already has a completed cloud QR payment",
                code="payment_already_completed",
            ) from exc
        raise CloudQrServiceError(
            "Bill already has an active cloud QR payment",
            code="active_attempt_exists",
        ) from exc

    bo = client or get_backoffice_qr_client()
    note = f"POS bill {bill.bill_number}"
    try:
        create_result = bo.create_qr(amount=float(bill.amount), note=note)
    except TigerBackOfficeQrError as exc:
        cloud_qr_repos.update_cloud_qr_payment(
            engine,
            payment_id,
            status="failed",
            error_message=exc.message,
            raw_create_response={
                "error": exc.message,
                "status_code": exc.status_code,
                "payload": exc.payload,
            },
        )
        raise CloudQrServiceError(
            f"BackOffice QR create failed: {exc.message}",
            code="cloud_qr_create_failed",
            details={"status_code": exc.status_code, "tiger": exc.payload},
        ) from exc

    uuid = str(create_result.get("uuid") or "").strip() or None
    ref1 = create_result.get("ref1")
    ref2 = create_result.get("ref2")
    qr_raw = create_result.get("qrRawData")
    qr_image = create_result.get("qrImage")
    updated = cloud_qr_repos.update_cloud_qr_payment(
        engine,
        payment_id,
        status="I",
        uuid=uuid,
        ref1=str(ref1) if ref1 is not None else None,
        ref2=str(ref2) if ref2 is not None else None,
        qr_raw_data=str(qr_raw) if isinstance(qr_raw, str) else None,
        qr_image=str(qr_image) if isinstance(qr_image, str) and qr_image.strip() else None,
        raw_create_response=create_result,
        clear_error=True,
    )
    stored = updated or row
    companion_payload = {
        "data": {
            "type": CLOUD_QR_PAYMENT_TYPE,
            "status": "pending",
            "amount": float(bill.amount),
            "dynamicQR": {
                "qrRawData": stored.get("qr_raw_data") or "",
                "qrImage": stored.get("qr_image") or "",
                "status": "I",
                "paymentGateway": settings.tiger_backoffice_qr_gateway,
                "refNo1": stored.get("ref1"),
                "refNo2": stored.get("ref2"),
            },
        }
    }
    return {
        "attempt": _public_cloud_row(stored),
        "cloud_qr": _public_cloud_row(stored),
        "create_response": omit_qr_images(create_result),
        "qr": companion_qr_from_cloud_row(stored)
        or extract_companion_qr(companion_payload),
        "payment_type": CLOUD_QR_PAYMENT_TYPE,
    }


def cancel_cloud_qr_payment(
    engine: Engine,
    payment_id: str,
    *,
    submitted_by: str | None = None,
    submitted_by_name: str | None = None,
) -> dict[str, Any]:
    row = cloud_qr_repos.get_cloud_qr_payment(engine, payment_id)
    if not row:
        raise CloudQrServiceError("Cloud QR payment not found", code="not_found")
    if not cloud_qr_repos.is_cloud_qr_active_status(str(row.get("status"))):
        raise CloudQrServiceError(
            "Cloud QR payment is not active",
            code="not_active",
        )
    actor_by, actor_name = normalize_submitter(
        line_user_id=submitted_by,
        display_name=submitted_by_name,
    )
    updated = cloud_qr_repos.update_cloud_qr_payment(
        engine,
        payment_id,
        status="X",
        clear_error=True,
    )
    logger.info(
        "cloud QR cancelled id=%s bill=%s by=%s/%s",
        payment_id,
        row.get("pos_bill_id"),
        actor_by,
        actor_name,
    )
    stored = updated or {**row, "status": "X"}
    return {
        "attempt": _public_cloud_row(stored),
        "cloud_qr": _public_cloud_row(stored),
        "qr": companion_qr_from_cloud_row(stored),
        "payment_type": CLOUD_QR_PAYMENT_TYPE,
    }


def poll_cloud_qr_once(
    engine: Engine,
    row: dict[str, Any],
    *,
    client: TigerBackOfficeQrClient | None = None,
) -> dict[str, Any] | None:
    payment_id = str(row.get("id") or "")
    uuid = str(row.get("uuid") or "").strip()
    if not payment_id or not uuid:
        return None
    if not cloud_qr_repos.is_cloud_qr_active_status(str(row.get("status"))):
        return None

    bo = client or get_backoffice_qr_client()
    try:
        status_payload = bo.get_qr_status(uuid)
    except TigerBackOfficeQrError as exc:
        logger.warning(
            "cloud QR status failed id=%s uuid=%s err=%s",
            payment_id,
            uuid,
            exc.message,
        )
        cloud_qr_repos.update_cloud_qr_payment(
            engine,
            payment_id,
            error_message=exc.message,
            touch_polled=True,
        )
        return None

    raw_status = str(status_payload.get("status") or "").strip().upper()
    if raw_status not in {"I", "C", "E", "X"}:
        cloud_qr_repos.update_cloud_qr_payment(
            engine,
            payment_id,
            raw_status_response=status_payload,
            touch_polled=True,
        )
        return cloud_qr_repos.get_cloud_qr_payment(engine, payment_id)

    kwargs: dict[str, Any] = {
        "status": raw_status,
        "raw_status_response": status_payload,
        "touch_polled": True,
        "clear_error": True,
    }
    if status_payload.get("payerName") is not None:
        kwargs["payer_name"] = str(status_payload.get("payerName") or "")
    if status_payload.get("payerAccountNumber") is not None:
        kwargs["payer_account_number"] = str(
            status_payload.get("payerAccountNumber") or ""
        )
    if status_payload.get("sendingBankCode") is not None:
        kwargs["sending_bank_code"] = str(status_payload.get("sendingBankCode") or "")
    if status_payload.get("amount") is not None:
        kwargs["paid_amount"] = status_payload.get("amount")
    if raw_status == "C":
        kwargs["set_paid_at"] = True

    return cloud_qr_repos.update_cloud_qr_payment(engine, payment_id, **kwargs)


def poll_active_cloud_qr_payments(engine: Engine) -> None:
    rows = cloud_qr_repos.list_active_cloud_qr_payments(engine)
    if not rows:
        return
    client = get_backoffice_qr_client()
    for row in rows:
        try:
            poll_cloud_qr_once(engine, row, client=client)
        except Exception:
            logger.exception(
                "cloud QR poll failed id=%s uuid=%s",
                row.get("id"),
                row.get("uuid"),
            )
