from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from src.tiger_pay.config import TigerPaySettings, get_tiger_pay_settings

logger = logging.getLogger("kcw.tiger_pay.voucher_api")

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


class TigerVoucherApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.payload = payload
        super().__init__(message)


def _normalize_host(api_host: str) -> str:
    host = (api_host or "").strip().rstrip("/")
    if not host:
        raise TigerVoucherApiError("TIGER_VOUCHER_API_HOST is not configured")
    return host


def _require_voucher_credentials(settings: TigerPaySettings) -> tuple[str, str, str, str]:
    host = _normalize_host(settings.tiger_voucher_api_host)
    username = settings.tiger_voucher_username.strip()
    password = settings.tiger_voucher_password.strip()
    mobile = settings.tiger_voucher_mobile.strip()
    if not username:
        raise TigerVoucherApiError("TIGER_VOUCHER_USERNAME is not configured")
    if not password:
        raise TigerVoucherApiError("TIGER_VOUCHER_PASSWORD is not configured")
    if not mobile:
        raise TigerVoucherApiError("TIGER_VOUCHER_MOBILE is not configured")
    return host, username, password, mobile


def _dig_token(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("token", "access_token"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for nest_key in ("success", "data"):
        nested = payload.get(nest_key)
        if isinstance(nested, dict):
            token = _dig_token(nested)
            if token:
                return token
    return None


_BOOLEANISH = frozenset({"true", "false", "yes", "no", "y", "n", "1", "0"})


def _looks_like_voucher_num(value: Any) -> str | None:
    """Return a cleaned voucher number, ignoring success flags / empty values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = str(int(value)) if float(value).is_integer() else str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or text.lower() in _BOOLEANISH:
        return None
    return text


def extract_voucher_num(payload: Any) -> str | None:
    if payload is None:
        return None
    direct = _looks_like_voucher_num(payload)
    if direct is not None and not isinstance(payload, (dict, list)):
        return direct
    if isinstance(payload, list):
        for item in payload:
            found = extract_voucher_num(item)
            if found:
                return found
        return None
    if not isinstance(payload, dict):
        return None
    for key in (
        "voucher_num",
        "voucherNum",
        "voucher_number",
        "voucherNumber",
        "voucher_no",
        "voucherNo",
        "number",
        "code",
    ):
        found = _looks_like_voucher_num(payload.get(key))
        if found:
            return found
    # Tiger create returns result: ["0824…"]; prefer that before success:"true".
    result = payload.get("result")
    if isinstance(result, list):
        found = extract_voucher_num(result)
        if found:
            return found
    for nest_key in ("voucher", "data", "items"):
        nested = payload.get(nest_key)
        if isinstance(nested, list) and nested:
            found = extract_voucher_num(nested[0])
            if found:
                return found
        elif isinstance(nested, dict):
            found = extract_voucher_num(nested)
            if found:
                return found
    # Only dig into success when it is an object (login-style), never "true"/"false".
    success = payload.get("success")
    if isinstance(success, dict):
        found = extract_voucher_num(success)
        if found:
            return found
    return None


def extract_voucher_display(payload: Any) -> dict[str, Any]:
    """Best-effort QR / code fields from create/show responses."""
    root = payload if isinstance(payload, dict) else {}
    data = root.get("data") if isinstance(root.get("data"), dict) else root
    if isinstance(data.get("voucher"), dict):
        data = data["voucher"]

    voucher_num = extract_voucher_num(payload)
    image = None
    raw = None
    code = None
    for key in ("qrImage", "qr_image", "image", "qr"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str) and value.strip():
            image = value.strip()
            break
    for key in ("qrRawData", "qr_raw_data", "qrRaw", "raw"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str) and value.strip():
            raw = value.strip()
            break
    for key in ("code", "voucher_code", "voucherCode"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, (str, int)) and str(value).strip():
            code = str(value).strip()
            break

    used = None
    if isinstance(data, dict):
        for key in ("used", "status", "voucher_status", "state"):
            value = data.get(key)
            if value is not None and str(value).strip():
                used = value
                break

    return {
        "voucher_num": voucher_num,
        "code": code or voucher_num,
        "qr_image": image,
        "qr_raw": raw,
        "raw_status": used,
    }


def normalize_voucher_status(raw: Any) -> str:
    if raw is None:
        return "unknown"
    text = str(raw).strip().lower()
    if not text:
        return "unknown"
    if text in {"y", "yes", "true", "1", "used", "redeemed", "success", "completed", "complete"}:
        return "used"
    if text in {"n", "no", "false", "0", "unused", "pending", "active", "created", "available"}:
        return "pending"
    if text in {"cancel", "canceled", "cancelled"}:
        return "cancelled"
    if text in {"expire", "expired"}:
        return "expired"
    if text in {"fail", "failed", "error"}:
        return "failed"
    return "unknown"


def voucher_validity_window(
    *,
    expire_hours: float,
    now: datetime | None = None,
) -> dict[str, str]:
    current = now or datetime.now(BANGKOK_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BANGKOK_TZ)
    else:
        current = current.astimezone(BANGKOK_TZ)
    expire_at = current + timedelta(hours=float(expire_hours))
    return {
        "start_date": current.strftime("%d-%m-%Y"),
        "expire_date": expire_at.strftime("%d-%m-%Y"),
        "start_time": current.strftime("%H:%M:%S"),
        "expire_time": expire_at.strftime("%H:%M:%S"),
    }


class TigerVoucherApiClient:
    def __init__(
        self,
        settings: TigerPaySettings | None = None,
        *,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.settings = settings or get_tiger_pay_settings()
        self.timeout_seconds = timeout_seconds
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, str] | None = None,
        token: str | None = None,
    ) -> tuple[int, Any]:
        host = _normalize_host(self.settings.tiger_voucher_api_host)
        url = f"{host}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(method, url, data=data, headers=headers)
        except httpx.HTTPError as exc:
            raise TigerVoucherApiError(f"Tiger voucher request failed: {exc}") from exc

        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text[:1000]}

        if response.status_code >= 400:
            message = "Tiger voucher API error"
            if isinstance(payload, dict):
                for key in ("message", "error", "detail"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        message = f"{message}: {value.strip()}"
                        break
            raise TigerVoucherApiError(
                message,
                status_code=response.status_code,
                payload=payload,
            )
        return response.status_code, payload

    def login(self, *, force: bool = False) -> str:
        now = time.time()
        if not force and self._token and now < self._token_expires_at:
            return self._token

        _host, username, password, mobile = _require_voucher_credentials(self.settings)
        _status, payload = self._request(
            "POST",
            "/api/tigerpay/login",
            data={
                "username": username,
                "password": password,
                "mobile": mobile,
            },
        )
        token = _dig_token(payload)
        if not token:
            raise TigerVoucherApiError(
                "Tiger voucher login did not return a token",
                payload=payload,
            )
        self._token = token
        # Tokens are opaque; refresh proactively every 30 minutes.
        self._token_expires_at = now + 30 * 60
        return token

    def _authed_request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, str] | None = None,
    ) -> Any:
        token = self.login()
        try:
            _status, payload = self._request(method, path, data=data, token=token)
            return payload
        except TigerVoucherApiError as exc:
            if exc.status_code not in {401, 403}:
                raise
            token = self.login(force=True)
            _status, payload = self._request(method, path, data=data, token=token)
            return payload

    def create_voucher(
        self,
        *,
        amount: float | int,
        ref_num: str,
        note: str = "",
        category: str = "CN",
        number_of_voucher: int = 1,
    ) -> dict[str, Any]:
        window = voucher_validity_window(
            expire_hours=self.settings.tiger_voucher_expire_hours,
        )
        amount_value: float | int = float(amount)
        if float(amount_value).is_integer():
            amount_value = int(amount_value)
        form = {
            "amount": str(amount_value),
            "number_of_voucher": str(int(number_of_voucher)),
            "start_date": window["start_date"],
            "expire_date": window["expire_date"],
            "start_time": window["start_time"],
            "expire_time": window["expire_time"],
            "ref_num": str(ref_num),
            "category": category or "CN",
            "note": note or "",
            "authen_required": self.settings.tiger_voucher_authen_required or "0",
            "approved_required": self.settings.tiger_voucher_approved_required or "0",
        }
        payload = self._authed_request("POST", "/api/voucher/create", data=form)
        return {"data": payload.get("data") if isinstance(payload, dict) else payload, "raw": payload}

    def show_voucher(self, voucher_num: str) -> dict[str, Any]:
        cleaned = str(voucher_num or "").strip()
        if not cleaned:
            raise TigerVoucherApiError("voucher_num is required")
        payload = self._authed_request("GET", f"/api/voucher/show/{cleaned}")
        return {"data": payload.get("data") if isinstance(payload, dict) else payload, "raw": payload}

    def cancel_voucher(self, voucher_num: str) -> dict[str, Any]:
        cleaned = str(voucher_num or "").strip()
        if not cleaned:
            raise TigerVoucherApiError("voucher_num is required")
        payload = self._authed_request("GET", f"/api/voucher/cancel/{cleaned}")
        return {"data": payload.get("data") if isinstance(payload, dict) else payload, "raw": payload}

    def query_vouchers(
        self,
        *,
        start_date: str,
        end_date: str,
        find_by: str = "created_date",
        used: str = "A",
    ) -> dict[str, Any]:
        payload = self._authed_request(
            "POST",
            "/api/voucher/query",
            data={
                "start_date": start_date,
                "end_date": end_date,
                "find_by": find_by,
                "used": used,
            },
        )
        return {"data": payload.get("data") if isinstance(payload, dict) else payload, "raw": payload}


def get_voucher_api_client(settings: TigerPaySettings | None = None) -> TigerVoucherApiClient:
    return TigerVoucherApiClient(settings=settings)
