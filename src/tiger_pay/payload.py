import copy
from typing import Any


def sanitize_webhook_payload(parsed_payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(parsed_payload)
    payment = sanitized.get("payment")
    if not isinstance(payment, dict):
        return sanitized

    dynamic_qr = payment.get("dynamicQR")
    if not isinstance(dynamic_qr, dict):
        return sanitized

    qr_image = dynamic_qr.get("qrImage")
    if isinstance(qr_image, str):
        dynamic_qr["qrImage"] = None
        dynamic_qr["qrImageOmitted"] = True
        dynamic_qr["qrImageLength"] = len(qr_image)

    return sanitized
