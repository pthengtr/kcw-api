from __future__ import annotations

import base64
import io
from typing import Any

import qrcode

from src.tiger_pay.status import TERMINAL_STATUSES, normalize_status

QR_PAYMENT_TYPES = frozenset({"qr", "promptpay"})
QR_PAID_STATUSES = frozenset({"c", "completed", "complete", "paid", "success"})


def payment_object_from_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and (
        "dynamicQR" in data or "paymentNo" in data or "type" in data or "id" in data
    ):
        return data
    payment = payload.get("payment")
    if isinstance(payment, dict):
        return payment
    if "dynamicQR" in payload or "paymentNo" in payload:
        return payload
    return None


def dynamic_qr_from_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        direct = payload.get("dynamicQR")
        if isinstance(direct, dict):
            return direct
    payment = payment_object_from_payload(payload)
    if isinstance(payment, dict):
        qr = payment.get("dynamicQR")
        if isinstance(qr, dict):
            return qr
    return None


def payment_type_from_payload(payload: Any) -> str | None:
    payment = payment_object_from_payload(payload)
    if not isinstance(payment, dict):
        return None
    raw = payment.get("type") or payment.get("payment_type")
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    return cleaned or None


def payment_type_from_attempt(attempt: dict[str, Any] | None) -> str | None:
    if not attempt:
        return None
    return payment_type_from_payload(attempt.get("raw_create_response"))


def has_displayable_qr(payload: Any) -> bool:
    """True when Tiger returned a non-empty QR image Companion can show.

    qrRawData alone is not enough — Companion only renders ``qr.image``.
    """
    qr = dynamic_qr_from_payload(payload)
    if not isinstance(qr, dict):
        return False
    if qr.get("qrImageOmitted"):
        return False
    image = qr.get("qrImage")
    return isinstance(image, str) and bool(image.strip())


def qr_image_src(qr_image: str) -> str:
    image = qr_image.strip()
    if image.startswith("data:"):
        return image
    return f"data:image/png;base64,{image}"


def render_qr_image_data_uri(raw_data: str) -> str:
    """Build a PNG data-URI from EMV / PromptPay payload text."""
    qr = qrcode.QRCode(border=2, box_size=6)
    qr.add_data(raw_data.strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def extract_companion_qr(payload: Any) -> dict[str, Any] | None:
    payment = payment_object_from_payload(payload) or {}
    qr = dynamic_qr_from_payload(payload)
    if not isinstance(qr, dict):
        return None

    image_raw = qr.get("qrImage")
    image = None
    if isinstance(image_raw, str) and image_raw.strip() and not qr.get("qrImageOmitted"):
        image = qr_image_src(image_raw)

    raw_data = qr.get("qrRawData")
    raw_text = raw_data.strip() if isinstance(raw_data, str) else ""
    # Tiger often returns empty qrImage with a valid EMV string — render locally.
    if image is None and raw_text:
        image = render_qr_image_data_uri(raw_text)

    status = qr.get("status") or qr.get("qrStatus")
    gateway = (
        qr.get("paymentGateway")
        or payment.get("paymentGateway")
        or qr.get("bank")
    )
    if image is None and not raw_text:
        if status is None and gateway is None:
            return None

    return {
        "image": image,
        "raw_data": raw_data if isinstance(raw_data, str) else None,
        "status": str(status).strip() if status is not None else None,
        "payment_gateway": str(gateway).strip() if gateway is not None else None,
        "transaction_id": qr.get("transactionId"),
        "ref_no_1": qr.get("refNo1"),
        "ref_no_2": qr.get("refNo2"),
    }


def companion_qr_from_attempt(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    if not attempt:
        return None
    return extract_companion_qr(attempt.get("raw_create_response"))


def merge_qr_payload_into_payment(
    payment: dict[str, Any],
    qr_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if not qr_result:
        return payment
    data = qr_result.get("data") if isinstance(qr_result.get("data"), dict) else qr_result
    if not isinstance(data, dict):
        return payment
    if isinstance(data.get("dynamicQR"), dict) or "paymentNo" in data:
        merged = dict(payment)
        merged.update(data)
        return merged
    if data.get("qrImage") or data.get("qrRawData"):
        merged = dict(payment)
        merged["dynamicQR"] = data
        return merged
    return payment


def dynamic_qr_is_paid(qr: dict[str, Any] | None) -> bool:
    if not isinstance(qr, dict):
        return False
    status = str(qr.get("status") or qr.get("qrStatus") or "").strip().lower()
    return status in QR_PAID_STATUSES


def _as_amount(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def should_confirm_qr_payment(payment: dict[str, Any] | None) -> bool:
    if not isinstance(payment, dict):
        return False
    payment_type = str(payment.get("type") or payment.get("payment_type") or "").strip().lower()
    qr = payment.get("dynamicQR") if isinstance(payment.get("dynamicQR"), dict) else None
    if payment_type not in QR_PAYMENT_TYPES and qr is None:
        return False

    status = normalize_status(str(payment.get("status") or ""))
    if status in TERMINAL_STATUSES:
        return False

    if dynamic_qr_is_paid(qr):
        return True

    amount = _as_amount(payment.get("amount"))
    total_pay = _as_amount(payment.get("totalPay"))
    if (
        amount is not None
        and total_pay is not None
        and amount > 0
        and total_pay + 1e-9 >= amount
        and (payment_type in QR_PAYMENT_TYPES or qr is not None)
    ):
        return True
    return False
