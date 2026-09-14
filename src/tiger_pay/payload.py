from typing import Any


def omit_qr_images(value: Any) -> Any:
    """Drop base64 QR images from stored/logged payloads; keep length metadata."""
    if isinstance(value, dict):
        qr_image = value.get("qrImage")
        out = {key: omit_qr_images(item) for key, item in value.items() if key != "qrImage"}
        if isinstance(qr_image, str):
            out["qrImage"] = None
            out["qrImageOmitted"] = True
            out["qrImageLength"] = len(qr_image)
        elif "qrImage" in value:
            out["qrImage"] = omit_qr_images(qr_image)
        return out
    if isinstance(value, list):
        return [omit_qr_images(item) for item in value]
    return value


def sanitize_webhook_payload(parsed_payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = omit_qr_images(parsed_payload)
    return sanitized if isinstance(sanitized, dict) else parsed_payload
