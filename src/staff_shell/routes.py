"""Mount /_shell/* routes on each staff FastAPI router."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from src.staff_shell.access_log import log_service_access
from src.staff_shell.auth import (
    SWITCH_HANDOFF_TTL_SECONDS,
    STAFF_COOKIE,
    clear_staff_session_cookie,
    identity_from_staff_cookie,
    set_staff_session_cookie,
)
from src.staff_shell.catalog import (
    can_access_service,
    filter_web_services,
    get_service,
    service_public_dict,
)
from src.staff_shell.urls import build_switch_url
from src.stock_check.auth import StockCheckIdentity


IdentityFn = Callable[[Request], StockCheckIdentity | None]
SecretFn = Callable[[], str]
IntFn = Callable[[], int]
StrFn = Callable[[], str]


class SwitchBody(BaseModel):
    service_id: str = Field(default="")


def _json_error(message: str, status: int = 400, code: str = "bad_request") -> JSONResponse:
    return JSONResponse({"error": code, "message": message}, status_code=status)


def resolve_shell_identity(
    request: Request,
    *,
    secret: str,
    site: str,
    app_identity: StockCheckIdentity | None,
) -> StockCheckIdentity | None:
    if app_identity is not None:
        return app_identity
    return identity_from_staff_cookie(
        request.cookies, secret=secret, expected_branch=site
    )


def mount_shell_routes(
    parent: APIRouter,
    *,
    current_service_id: str,
    session_cookie: str,
    session_cookie_path: str,
    get_secret: SecretFn,
    get_ttl: IntFn,
    get_site: StrFn,
    get_app_identity: IdentityFn,
    get_access_group: Callable[[StockCheckIdentity], str | None] | None = None,
) -> None:
    """Attach GET me/services and POST switch/logout under ``/_shell``."""

    shell = APIRouter(prefix="/_shell", tags=["staff-shell"])

    def _ident(request: Request) -> tuple[StockCheckIdentity | None, JSONResponse | None]:
        secret = (get_secret() or "").strip()
        if not secret:
            return None, _json_error("token secret missing", 500, "config")
        site = (get_site() or "HQ").upper()
        app_ident = None
        try:
            app_ident = get_app_identity(request)
        except Exception:  # noqa: BLE001
            app_ident = None
        ident = resolve_shell_identity(
            request, secret=secret, site=site, app_identity=app_ident
        )
        if ident is None:
            return None, _json_error("ต้องเปิดลิงก์จาก LINE", 401, "unauthorized")
        return ident, None

    def _group(ident: StockCheckIdentity) -> str | None:
        if get_access_group:
            try:
                return get_access_group(ident)
            except Exception:  # noqa: BLE001
                return None
        return None

    @shell.get("/me")
    def shell_me(request: Request) -> Any:
        ident, err = _ident(request)
        if err:
            return err
        assert ident is not None
        site = (get_site() or "HQ").upper()
        return {
            "line_user_id": ident.line_user_id,
            "display_name": ident.display_name,
            "branch": (ident.branch or site).upper(),
            "site": site,
            "service_id": current_service_id,
        }

    @shell.get("/services")
    def shell_services(request: Request) -> Any:
        ident, err = _ident(request)
        if err:
            return err
        assert ident is not None
        site = (get_site() or "HQ").upper()
        group = _group(ident)
        services = filter_web_services(
            site=site, access_group=group, is_allowed=True
        )
        return {
            "site": site,
            "current": current_service_id,
            "services": [
                service_public_dict(s, current=(s.id == current_service_id))
                for s in services
            ],
        }

    @shell.post("/switch")
    def shell_switch(request: Request, body: SwitchBody) -> Any:
        ident, err = _ident(request)
        if err:
            return err
        assert ident is not None
        secret = get_secret().strip()
        site = (get_site() or "HQ").upper()
        target_id = (body.service_id or "").strip()
        target = get_service(target_id)
        if not target:
            return _json_error("ไม่พบบริการนี้", 404, "not_found")
        if target.id == current_service_id:
            return {"url": target.path, "service_id": target.id, "same": True}
        if site not in target.hosts:
            return _json_error("บริการนี้ไม่มีบนสาขานี้", 403, "wrong_host")
        group = _group(ident)
        if not can_access_service(target.id, access_group=group, is_allowed=True):
            return _json_error("ไม่มีสิทธิ์ใช้บริการนี้", 403, "forbidden")

        ttl = min(SWITCH_HANDOFF_TTL_SECONDS, max(get_ttl(), 60))
        try:
            url = build_switch_url(
                request,
                target,
                secret=secret,
                line_user_id=ident.line_user_id,
                display_name=ident.display_name,
                branch=ident.branch or site,
                ttl_seconds=ttl,
            )
        except Exception as exc:  # noqa: BLE001
            return _json_error(f"สร้างลิงก์ไม่สำเร็จ: {exc}", 500, "mint_failed")

        log_service_access(
            line_user_id=ident.line_user_id,
            display_name=ident.display_name,
            branch=ident.branch or site,
            service_id=target.id,
            source="launcher",
            action="switch",
            path=target.path,
        )
        # Refresh staff session so idle hops keep working.
        resp = JSONResponse({"url": url, "service_id": target.id, "same": False})
        set_staff_session_cookie(
            resp, ident, secret=secret, ttl_seconds=max(get_ttl(), 3600)
        )
        return resp

    @shell.post("/logout")
    def shell_logout(request: Request) -> Any:
        secret = (get_secret() or "").strip()
        site = (get_site() or "HQ").upper()
        ident = None
        try:
            ident = get_app_identity(request)
        except Exception:  # noqa: BLE001
            ident = None
        if ident is None and secret:
            ident = identity_from_staff_cookie(
                request.cookies, secret=secret, expected_branch=site
            )
        if ident is not None:
            log_service_access(
                line_user_id=ident.line_user_id,
                display_name=ident.display_name,
                branch=ident.branch or site,
                service_id=current_service_id,
                source="launcher",
                action="logout",
            )
        resp = JSONResponse({"ok": True})
        clear_staff_session_cookie(resp)
        resp.delete_cookie(session_cookie, path=session_cookie_path)
        # Also clear cookie if path was default / without trailing rules.
        if session_cookie_path != "/":
            resp.delete_cookie(session_cookie, path="/")
        # Drop leftover staff cookie name from mis-set paths.
        resp.delete_cookie(STAFF_COOKIE, path="/")
        return resp

    parent.include_router(shell)
