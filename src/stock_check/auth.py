from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class StockCheckIdentity:
    line_user_id: str
    display_name: str
    branch: str
    app: str = "stock-check"


class TokenError(ValueError):
    pass


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    import base64

    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def mint_access_token(
    *,
    secret: str,
    line_user_id: str,
    display_name: str,
    branch: str,
    ttl_seconds: int,
    app: str = "stock-check",
    now: float | None = None,
) -> str:
    if not secret:
        raise TokenError("STOCK_CHECK_TOKEN_SECRET is not configured")
    ts = int(now if now is not None else time.time())
    payload = {
        "uid": line_user_id,
        "name": display_name or line_user_id,
        "branch": branch,
        "app": app,
        "iat": ts,
        "exp": ts + int(ttl_seconds),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _b64url(
        hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{body}.{sig}"


def verify_access_token(
    token: str,
    *,
    secret: str,
    expected_branch: str,
    expected_app: str = "stock-check",
    now: float | None = None,
) -> StockCheckIdentity:
    if not secret:
        raise TokenError("STOCK_CHECK_TOKEN_SECRET is not configured")
    if not token or "." not in token:
        raise TokenError("invalid token")
    body, sig = token.rsplit(".", 1)
    expected = _b64url(
        hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig, expected):
        raise TokenError("invalid token signature")
    try:
        payload: dict[str, Any] = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TokenError("invalid token payload") from exc
    ts = int(now if now is not None else time.time())
    if int(payload.get("exp") or 0) < ts:
        raise TokenError("token expired")
    branch = str(payload.get("branch") or "").upper()
    if branch != expected_branch.upper():
        raise TokenError("token branch mismatch")
    uid = str(payload.get("uid") or "").strip()
    if not uid:
        raise TokenError("token missing user")
    name = str(payload.get("name") or uid).strip() or uid
    app = str(payload.get("app") or "stock-check").strip() or "stock-check"
    if app != expected_app:
        raise TokenError("token app mismatch")
    return StockCheckIdentity(
        line_user_id=uid,
        display_name=name,
        branch=branch,
        app=app,
    )


def build_entry_url(base_url: str, token: str, path: str = "/stock-check/") -> str:
    root = (base_url or "").rstrip("/")
    prefix = path if path.startswith("/") else f"/{path}"
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    return f"{root}{prefix}?{urlencode({'t': token})}"


def quote_path(value: str) -> str:
    return quote(value, safe="")
