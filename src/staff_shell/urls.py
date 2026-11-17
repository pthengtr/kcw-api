"""Build cross-service handoff URLs on the same host (port rewrite)."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from fastapi import Request

from src.staff_shell.catalog import ServiceDef
from src.stock_check.auth import build_entry_url, mint_access_token


def request_base_url(request: Request) -> str:
    """Scheme + host[:port] as the browser sees this service."""
    # Prefer proxy headers when present (future reverse proxy).
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    if not host:
        host = request.url.netloc
    return f"{proto}://{host}".rstrip("/")


def rewrite_base_port(url: str | None, port: int) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    host = parts.hostname or ""
    if not host:
        return None
    netloc = f"{host}:{int(port)}"
    if parts.username:
        user = parts.username
        if parts.password:
            user = f"{user}:{parts.password}"
        netloc = f"{user}@{netloc}"
    return urlunsplit((parts.scheme or "http", netloc, "", "", ""))


def build_switch_url(
    request: Request,
    target: ServiceDef,
    *,
    secret: str,
    line_user_id: str,
    display_name: str,
    branch: str,
    ttl_seconds: int,
) -> str:
    base = rewrite_base_port(request_base_url(request), target.port) or request_base_url(request)
    token = mint_access_token(
        secret=secret,
        line_user_id=line_user_id,
        display_name=display_name,
        branch=branch,
        ttl_seconds=ttl_seconds,
        app=target.app,
    )
    return build_entry_url(base, token, path=target.path)
