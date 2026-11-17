"""Shared staff session cookie (identity across services on the same host)."""

from __future__ import annotations

from typing import Any

from fastapi.responses import Response

from src.stock_check.auth import (
    StockCheckIdentity,
    TokenError,
    mint_access_token,
    verify_access_token,
)

STAFF_APP = "kcw-staff"
STAFF_COOKIE = "kcw_staff_session"
STAFF_COOKIE_PATH = "/"
SWITCH_HANDOFF_TTL_SECONDS = 300


def mint_staff_token(
    *,
    secret: str,
    line_user_id: str,
    display_name: str,
    branch: str,
    ttl_seconds: int,
) -> str:
    return mint_access_token(
        secret=secret,
        line_user_id=line_user_id,
        display_name=display_name,
        branch=branch,
        ttl_seconds=ttl_seconds,
        app=STAFF_APP,
    )


def verify_staff_token(
    token: str,
    *,
    secret: str,
    expected_branch: str | None = None,
) -> StockCheckIdentity:
    """Verify staff session. Branch check is optional (multi-site cookies)."""
    if not secret:
        raise TokenError("token secret missing")
    if expected_branch:
        return verify_access_token(
            token,
            secret=secret,
            expected_branch=expected_branch,
            expected_app=STAFF_APP,
        )
    # Reuse verify with a two-pass HQ/SYP attempt when branch unknown.
    last: Exception | None = None
    for branch in ("HQ", "SYP"):
        try:
            return verify_access_token(
                token,
                secret=secret,
                expected_branch=branch,
                expected_app=STAFF_APP,
            )
        except TokenError as exc:
            last = exc
            continue
    raise TokenError(str(last) if last else "invalid staff token")


def identity_from_staff_cookie(
    request_cookies: Any,
    *,
    secret: str,
    expected_branch: str | None = None,
) -> StockCheckIdentity | None:
    token = (request_cookies.get(STAFF_COOKIE) or "").strip()
    if not token:
        return None
    try:
        return verify_staff_token(
            token, secret=secret, expected_branch=expected_branch
        )
    except TokenError:
        return None


def set_staff_session_cookie(
    response: Response,
    identity: StockCheckIdentity,
    *,
    secret: str,
    ttl_seconds: int,
) -> str:
    ttl = max(int(ttl_seconds), 3600)
    token = mint_staff_token(
        secret=secret,
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        ttl_seconds=ttl,
    )
    response.set_cookie(
        STAFF_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=ttl,
        path=STAFF_COOKIE_PATH,
    )
    return token


def clear_staff_session_cookie(response: Response) -> None:
    response.delete_cookie(STAFF_COOKIE, path=STAFF_COOKIE_PATH)


def attach_staff_session(
    response: Response,
    identity: StockCheckIdentity,
    *,
    secret: str,
    ttl_seconds: int,
    service_id: str,
    source: str = "line",
    path: str | None = None,
    log_open: bool = True,
) -> None:
    """Set staff cookie; optionally write an access-log open event."""
    from src.staff_shell.access_log import log_service_access

    if not secret or not identity:
        return
    set_staff_session_cookie(
        response, identity, secret=secret, ttl_seconds=ttl_seconds
    )
    if not log_open:
        return
    log_service_access(
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        service_id=service_id,
        source=source,
        action="open",
        path=path,
    )
