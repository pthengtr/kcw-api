from __future__ import annotations

from typing import Any


TAILSCALE_USER_ID = "tailscale"
TAILSCALE_DISPLAY_NAME = "Tailscale account"


def normalize_submitter(
    *,
    line_user_id: str | None = None,
    display_name: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (submitted_by, submitted_by_name) for persistence / event payloads."""
    uid = str(line_user_id or "").strip() or None
    if not uid:
        return None, None
    if uid == TAILSCALE_USER_ID:
        return TAILSCALE_USER_ID, TAILSCALE_DISPLAY_NAME
    name = str(display_name or "").strip() or uid
    return uid, name


def submitter_from_identity(identity: Any | None) -> tuple[str | None, str | None]:
    if identity is None:
        return None, None
    return normalize_submitter(
        line_user_id=getattr(identity, "line_user_id", None),
        display_name=getattr(identity, "display_name", None),
    )


def submitter_payload(
    *,
    submitted_by: str | None,
    submitted_by_name: str | None,
) -> dict[str, str]:
    out: dict[str, str] = {}
    if submitted_by:
        out["submitted_by"] = submitted_by
    if submitted_by_name:
        out["submitted_by_name"] = submitted_by_name
    return out
