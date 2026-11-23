from __future__ import annotations

import time
from typing import Any

SESSION_TTL_SECONDS = 600

# line_user_id -> session dict
_SESSIONS: dict[str, dict[str, Any]] = {}

END_WORDS = {"ยกเลิก", "cancel", "จบ", "เสร็จ"}


def _now() -> float:
    return time.time()


def clear_session(line_user_id: str | None) -> None:
    if not line_user_id:
        return
    _SESSIONS.pop(line_user_id, None)


def get_session(line_user_id: str | None) -> dict[str, Any] | None:
    if not line_user_id:
        return None
    session = _SESSIONS.get(line_user_id)
    if not session:
        return None
    if _now() - float(session.get("started_at") or 0) > SESSION_TTL_SECONDS:
        _SESSIONS.pop(line_user_id, None)
        return None
    return session


def start_request_session(line_user_id: str) -> dict[str, Any]:
    session = {
        "kind": "request",
        "step": "await_reason",
        "started_at": _now(),
        "reason": None,
    }
    _SESSIONS[line_user_id] = session
    return session


def start_admin_note_session(
    line_user_id: str,
    *,
    action: str,
    request_id: str,
    short_code: int,
) -> dict[str, Any]:
    session = {
        "kind": "admin_note",
        "action": action,  # needs_info | reject
        "request_id": request_id,
        "short_code": short_code,
        "started_at": _now(),
    }
    _SESSIONS[line_user_id] = session
    return session


def start_extra_reason_session(
    line_user_id: str, *, request_id: str, short_code: int
) -> dict[str, Any]:
    session = {
        "kind": "extra_reason",
        "request_id": request_id,
        "short_code": short_code,
        "started_at": _now(),
    }
    _SESSIONS[line_user_id] = session
    return session


def touch(session: dict[str, Any]) -> None:
    session["started_at"] = _now()


def reset_sessions_for_tests() -> None:
    _SESSIONS.clear()
