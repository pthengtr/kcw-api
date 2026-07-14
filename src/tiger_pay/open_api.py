from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import jwt

from src.tiger_pay.config import TigerPaySettings, get_tiger_pay_settings
from src.tiger_pay.digest import compute_body_sha256

logger = logging.getLogger("kcw.tiger_pay.open_api")


class TigerPayOpenApiError(Exception):
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


def _normalize_api_host(api_host: str) -> str:
    host = api_host.strip()
    if not host:
        raise TigerPayOpenApiError("TIGER_PAY_API_HOST is not configured")
    if not host.endswith("/"):
        host = f"{host}/"
    return host


def _require_open_api_credentials(settings: TigerPaySettings) -> tuple[str, str, str]:
    client_id = settings.tiger_pay_client_id.strip()
    client_secret = settings.tiger_pay_client_secret.strip()
    api_host = settings.tiger_pay_api_host.strip()
    if not client_id:
        raise TigerPayOpenApiError("TIGER_PAY_CLIENT_ID is not configured")
    if not client_secret:
        raise TigerPayOpenApiError("TIGER_PAY_CLIENT_SECRET is not configured")
    if not api_host:
        raise TigerPayOpenApiError("TIGER_PAY_API_HOST is not configured")
    return client_id, client_secret, _normalize_api_host(api_host)


def build_open_api_authorization(
    *,
    client_id: str,
    client_secret: str,
    raw_body: bytes | None = None,
) -> str:
    claims: dict[str, str] = {"clientId": client_id}
    if raw_body is not None:
        claims["messageDigest"] = compute_body_sha256(raw_body)
    token = jwt.encode(claims, client_secret, algorithm="HS256")
    return f"Bearer {token}"


def _parse_envelope(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        raise TigerPayOpenApiError("Unexpected Tiger Pay response shape", payload=payload)
    return payload.get("data")


class TigerPayOpenApiClient:
    def __init__(
        self,
        settings: TigerPaySettings | None = None,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.settings = settings or get_tiger_pay_settings()
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        include_digest: bool = False,
    ) -> tuple[int, Any]:
        client_id, client_secret, api_host = _require_open_api_credentials(self.settings)
        url = f"{api_host}{path.lstrip('/')}"

        raw_body: bytes | None = None
        headers = {"Accept": "application/json"}
        if json_body is not None:
            raw_body = json.dumps(json_body, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
            headers["Content-Type"] = "application/json"

        authorization = build_open_api_authorization(
            client_id=client_id,
            client_secret=client_secret,
            raw_body=raw_body if include_digest else None,
        )
        headers["Authorization"] = authorization

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.request(
                method,
                url,
                content=raw_body,
                headers=headers,
            )

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        return response.status_code, payload

    def get_current(self) -> dict[str, Any] | None:
        status_code, payload = self._request("GET", "api/open/v2/payment/current")
        if status_code == 404:
            return None
        if status_code >= 400:
            raise TigerPayOpenApiError(
                "Failed to get current payment",
                status_code=status_code,
                payload=payload,
            )
        return _parse_envelope(payload)

    def get_payment(self, tiger_payment_id: int | str) -> dict[str, Any]:
        status_code, payload = self._request(
            "GET",
            f"api/open/v2/payment/{tiger_payment_id}",
        )
        if status_code >= 400:
            raise TigerPayOpenApiError(
                "Failed to get payment",
                status_code=status_code,
                payload=payload,
            )
        data = _parse_envelope(payload)
        if not isinstance(data, dict):
            raise TigerPayOpenApiError(
                "Payment not found in response",
                status_code=status_code,
                payload=payload,
            )
        return data

    def create_payment(
        self,
        *,
        amount: float | int | str,
        ref_no_1: str,
        ref_no_2: str,
        note: str,
        payment_type: str = "cash",
    ) -> dict[str, Any]:
        body = {
            "type": payment_type,
            "amount": amount,
            "note": note,
            "refNo1": ref_no_1,
            "refNo2": ref_no_2,
        }
        status_code, payload = self._request(
            "POST",
            "api/open/v2/payment",
            json_body=body,
            include_digest=True,
        )
        if status_code >= 400:
            raise TigerPayOpenApiError(
                "Failed to create payment",
                status_code=status_code,
                payload=payload,
            )
        data = _parse_envelope(payload)
        if not isinstance(data, dict):
            raise TigerPayOpenApiError(
                "Create payment returned empty data",
                status_code=status_code,
                payload=payload,
            )
        return {"data": data, "message": payload.get("message"), "raw": payload}

    def cancel_payment(
        self,
        tiger_payment_id: int | str,
        *,
        note: str = "",
    ) -> dict[str, Any]:
        body = {"note": note}
        status_code, payload = self._request(
            "PUT",
            f"api/open/v2/payment/{tiger_payment_id}/cancel",
            json_body=body,
            include_digest=False,
        )
        if status_code >= 400:
            raise TigerPayOpenApiError(
                "Failed to cancel payment",
                status_code=status_code,
                payload=payload,
            )
        data = _parse_envelope(payload)
        return {"data": data, "message": payload.get("message"), "raw": payload}


def get_open_api_client() -> TigerPayOpenApiClient:
    return TigerPayOpenApiClient()
