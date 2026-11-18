from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import httpx

from src.tiger_pay.config import TigerPaySettings, get_tiger_pay_settings

logger = logging.getLogger("kcw.tiger_pay.backoffice_qr")


class TigerBackOfficeQrError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
        no_response: bool = False,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.payload = payload
        self.no_response = no_response
        super().__init__(message)


def _normalize_base(url: str) -> str:
    host = (url or "").strip()
    if not host:
        raise TigerBackOfficeQrError("TIGER_BACKOFFICE_BASE is not configured")
    return host if host.endswith("/") else f"{host}/"


class TigerBackOfficeQrClient:
    """Tiger BackOffice cloud QR (KBANK) — no auth headers; identity is serial."""

    def __init__(
        self,
        settings: TigerPaySettings | None = None,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.settings = settings or get_tiger_pay_settings()
        self.timeout_seconds = timeout_seconds
        self._http: httpx.Client | None = None

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=self.timeout_seconds)
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def _require_serial(self) -> str:
        serial = self.settings.tiger_box_serial.strip()
        if not serial:
            raise TigerBackOfficeQrError("TIGER_BOX_SERIAL is not configured")
        return serial

    def create_qr(
        self,
        *,
        amount: float | int | str,
        note: str = "",
        payment_gateway: str | None = None,
        service_id: str | None = None,
        serial: str | None = None,
    ) -> dict[str, Any]:
        base = _normalize_base(self.settings.tiger_backoffice_base)
        gateway = (payment_gateway or self.settings.tiger_backoffice_qr_gateway).strip().upper()
        sid = (service_id or self.settings.tiger_backoffice_service_id).strip() or "3"
        box_serial = (serial or self._require_serial()).strip()

        if isinstance(amount, float) and amount.is_integer():
            amount_value: float | int = int(amount)
        else:
            try:
                as_float = float(amount)
                amount_value = int(as_float) if as_float.is_integer() else as_float
            except (TypeError, ValueError):
                amount_value = amount

        form = {
            "service_id": sid,
            "amount": str(amount_value),
            "note": note or "",
            "payment_gateway": gateway,
            "serial": box_serial,
        }
        url = f"{base}pos/api/qr/create"
        try:
            response = self._client().post(url, data=form)
        except httpx.TimeoutException as exc:
            raise TigerBackOfficeQrError(
                "Tiger BackOffice QR create timed out",
                payload={"url": url, "form": form},
                no_response=True,
            ) from exc
        except httpx.RequestError as exc:
            raise TigerBackOfficeQrError(
                f"Tiger BackOffice QR create failed: {exc}",
                payload={"url": url, "form": form},
                no_response=True,
            ) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            message = "Failed to create BackOffice QR"
            if isinstance(payload, dict):
                err = payload.get("error") or payload.get("message")
                if isinstance(err, str) and err.strip():
                    message = f"{message}: {err.strip()}"
            raise TigerBackOfficeQrError(
                message,
                status_code=response.status_code,
                payload=payload,
            )

        if not isinstance(payload, dict) or not payload.get("success"):
            raise TigerBackOfficeQrError(
                "BackOffice QR create returned unsuccessful payload",
                status_code=response.status_code,
                payload=payload,
            )
        return payload

    def get_qr_status(self, uuid: str) -> dict[str, Any]:
        cleaned = str(uuid or "").strip()
        if not cleaned:
            raise TigerBackOfficeQrError("QR uuid is required")
        base = _normalize_base(self.settings.tiger_backoffice_base)
        url = f"{base}pos/api/qr/status/{cleaned}"
        try:
            response = self._client().get(url)
        except httpx.TimeoutException as exc:
            raise TigerBackOfficeQrError(
                "Tiger BackOffice QR status timed out",
                payload={"url": url},
                no_response=True,
            ) from exc
        except httpx.RequestError as exc:
            raise TigerBackOfficeQrError(
                f"Tiger BackOffice QR status failed: {exc}",
                payload={"url": url},
                no_response=True,
            ) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            message = "Failed to get BackOffice QR status"
            if isinstance(payload, dict):
                err = payload.get("error") or payload.get("message")
                if isinstance(err, str) and err.strip():
                    message = f"{message}: {err.strip()}"
            raise TigerBackOfficeQrError(
                message,
                status_code=response.status_code,
                payload=payload,
            )
        if not isinstance(payload, dict):
            raise TigerBackOfficeQrError(
                "Unexpected BackOffice QR status shape",
                status_code=response.status_code,
                payload=payload,
            )
        return payload


@lru_cache(maxsize=1)
def get_backoffice_qr_client() -> TigerBackOfficeQrClient:
    return TigerBackOfficeQrClient()
