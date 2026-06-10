import os
import time
import uuid
from typing import Any

PRINTOUT_TTL_SECONDS = int(os.getenv("PRINTOUT_TTL_SECONDS", "3600").strip())

_PRINTOUTS: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _purge_expired():
    now = _now()
    expired = [
        token
        for token, item in _PRINTOUTS.items()
        if float(item.get("expires_at") or 0) < now
    ]
    for token in expired:
        _PRINTOUTS.pop(token, None)


def save_printout(
    extracted: dict[str, Any],
    *,
    line_user_id: str | None = None,
    source: str = "line",
) -> str:
    _purge_expired()

    token = uuid.uuid4().hex
    _PRINTOUTS[token] = {
        "token": token,
        "extracted": extracted,
        "line_user_id": (line_user_id or "").strip(),
        "source": source,
        "created_at": _now(),
        "expires_at": _now() + PRINTOUT_TTL_SECONDS,
    }
    return token


def get_printout(token: str) -> dict[str, Any] | None:
    _purge_expired()

    item = _PRINTOUTS.get((token or "").strip())
    if not item:
        return None

    if float(item.get("expires_at") or 0) < _now():
        _PRINTOUTS.pop(item["token"], None)
        return None

    return item
