"""Small helpers so each staff router can adopt the shell consistently."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import Response

from src.staff_shell.auth import attach_staff_session
from src.staff_shell.routes import mount_shell_routes
from src.staff_shell.ui import inject_shell
from src.stock_check.auth import StockCheckIdentity


def shell_page(
    html: str,
    *,
    service_id: str,
    api_base: str,
    user_name: str = "",
    branch: str = "",
) -> str:
    return inject_shell(
        html,
        service_id=service_id,
        api_base=api_base,
        user_name=user_name,
        branch=branch,
    )


def stamp_staff_session(
    response: Response,
    identity: StockCheckIdentity | None,
    *,
    secret: str,
    ttl_seconds: int,
    service_id: str,
    source: str = "line",
    path: str | None = None,
    log_open: bool = False,
) -> None:
    if identity is None or not secret:
        return
    attach_staff_session(
        response,
        identity,
        secret=secret,
        ttl_seconds=ttl_seconds,
        service_id=service_id,
        source=source,
        path=path,
        log_open=log_open,
    )


def entry_source(*, had_staff_cookie: bool, has_entry_token: bool) -> tuple[str, bool]:
    """Return (source, log_open) for a page entry."""
    if has_entry_token:
        return ("launcher" if had_staff_cookie else "line", True)
    return ("direct", False)


def wire_shell(
    router: APIRouter,
    *,
    current_service_id: str,
    session_cookie: str,
    session_cookie_path: str,
    get_secret: Callable[[], str],
    get_ttl: Callable[[], int],
    get_site: Callable[[], str],
    get_app_identity: Callable[[Request], StockCheckIdentity | None],
) -> None:
    mount_shell_routes(
        router,
        current_service_id=current_service_id,
        session_cookie=session_cookie,
        session_cookie_path=session_cookie_path,
        get_secret=get_secret,
        get_ttl=get_ttl,
        get_site=get_site,
        get_app_identity=get_app_identity,
    )
