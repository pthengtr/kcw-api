import hmac
import re

import jwt

from src.tiger_pay.digest import compute_body_sha256

SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class TigerPayAuthError(Exception):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise TigerPayAuthError("authorization_missing")

    parts = authorization.split(None, 1)
    if len(parts) != 2:
        raise TigerPayAuthError("authorization_scheme_invalid")

    scheme, token = parts
    if scheme.lower() != "bearer":
        raise TigerPayAuthError("authorization_scheme_invalid")

    token = token.strip()
    if not token:
        raise TigerPayAuthError("authorization_scheme_invalid")

    return token


def _normalize_message_digest(value: object) -> str:
    if not isinstance(value, str):
        raise TigerPayAuthError("digest_missing")

    digest = value.strip().lower()
    if not SHA256_HEX_RE.fullmatch(digest):
        raise TigerPayAuthError("digest_invalid")

    return digest


def verify_webhook_authorization(
    authorization: str | None,
    raw_body: bytes,
    client_secret: str,
) -> None:
    token = _parse_bearer_token(authorization)

    try:
        claims = jwt.decode(
            token,
            client_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise TigerPayAuthError("jwt_invalid") from None

    message_digest = _normalize_message_digest(claims.get("messageDigest"))
    body_sha256 = compute_body_sha256(raw_body)

    if not hmac.compare_digest(body_sha256, message_digest):
        raise TigerPayAuthError("digest_mismatch")
